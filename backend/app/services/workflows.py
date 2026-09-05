"""Workflow persistence and lifecycle operations.

Every function takes the requesting user so ownership is enforced in one
place rather than in each route.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.core.security import generate_webhook_token
from app.models import User, Workflow, WorkflowEdge, WorkflowNode, WorkflowStatus

DUPLICATE_SUFFIX = " (copy)"
LIKE_ESCAPE = "\\"
MAX_NAME_LENGTH = 120


@dataclass(frozen=True, slots=True)
class WorkflowListResult:
    workflows: list[Workflow]
    node_counts: dict[uuid.UUID, int]
    total: int


def _owned(user: User) -> Select[tuple[Workflow]]:
    return select(Workflow).where(Workflow.owner_id == user.id)


def get_workflow(session: Session, user: User, workflow_id: uuid.UUID) -> Workflow:
    """Return a workflow owned by ``user``.

    A workflow belonging to someone else reports as missing rather than
    forbidden, so the endpoint cannot confirm that an id exists.
    """
    workflow = session.scalar(_owned(user).where(Workflow.id == workflow_id))
    if workflow is None:
        raise NotFoundError("Workflow not found.")
    return workflow


def list_workflows(
    session: Session,
    user: User,
    *,
    search: str | None = None,
    status: WorkflowStatus | None = None,
    limit: int = 20,
    offset: int = 0,
) -> WorkflowListResult:
    """Return a page of the user's workflows, newest activity first."""
    query = _owned(user)

    if search:
        # Bound as a parameter, so the term is never interpolated into SQL. LIKE
        # wildcards are escaped so a search for "50%" is matched literally.
        pattern = f"%{_escape_like(search.strip())}%"
        query = query.where(
            or_(
                Workflow.name.ilike(pattern, escape=LIKE_ESCAPE),
                Workflow.description.ilike(pattern, escape=LIKE_ESCAPE),
            )
        )
    if status is not None:
        query = query.where(Workflow.status == status)

    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    workflows = list(
        session.scalars(
            query.order_by(Workflow.updated_at.desc()).limit(limit).offset(offset)
        ).all()
    )

    return WorkflowListResult(
        workflows=workflows,
        node_counts=count_nodes(session, [workflow.id for workflow in workflows]),
        total=total,
    )


def _escape_like(term: str) -> str:
    """Escape the LIKE wildcards so user input matches literally."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def count_nodes(session: Session, workflow_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    """Node counts for several workflows in a single query."""
    if not workflow_ids:
        return {}

    rows = (
        session.execute(
            select(WorkflowNode.workflow_id, func.count(WorkflowNode.id))
            .where(WorkflowNode.workflow_id.in_(workflow_ids))
            .group_by(WorkflowNode.workflow_id)
        )
        .tuples()
        .all()
    )
    counts = dict(rows)
    return {workflow_id: counts.get(workflow_id, 0) for workflow_id in workflow_ids}


def create_workflow(session: Session, user: User, *, name: str, description: str = "") -> Workflow:
    workflow = Workflow(
        owner_id=user.id,
        name=name,
        description=description,
        status=WorkflowStatus.DRAFT,
        webhook_token=generate_webhook_token(),
    )
    session.add(workflow)
    session.flush()
    return workflow


def update_workflow(
    session: Session,
    workflow: Workflow,
    *,
    name: str | None = None,
    description: str | None = None,
    status: WorkflowStatus | None = None,
) -> Workflow:
    if name is not None:
        workflow.name = name
    if description is not None:
        workflow.description = description
    if status is not None:
        workflow.status = status
    session.flush()
    return workflow


def delete_workflow(session: Session, workflow: Workflow) -> None:
    """Delete a workflow along with its graph and its run history."""
    session.delete(workflow)
    session.flush()


def duplicate_workflow(session: Session, user: User, workflow: Workflow) -> Workflow:
    """Copy a workflow's graph into a new draft.

    Run history is not copied: it belongs to the original workflow.
    """
    copy = create_workflow(
        session,
        user,
        name=_duplicate_name(workflow.name),
        description=workflow.description,
    )

    node_id_map: dict[uuid.UUID, uuid.UUID] = {}
    for node in workflow.nodes:
        new_node = WorkflowNode(
            workflow_id=copy.id,
            node_type=node.node_type,
            label=node.label,
            configuration=dict(node.configuration),
            position_x=node.position_x,
            position_y=node.position_y,
        )
        session.add(new_node)
        session.flush()
        node_id_map[node.id] = new_node.id

    for edge in workflow.edges:
        session.add(
            WorkflowEdge(
                workflow_id=copy.id,
                source_node_id=node_id_map[edge.source_node_id],
                target_node_id=node_id_map[edge.target_node_id],
                source_handle=edge.source_handle,
                target_handle=edge.target_handle,
            )
        )

    session.flush()
    return copy


def _duplicate_name(name: str) -> str:
    """Append a copy suffix, trimming the base name if it would overflow."""
    if len(name) + len(DUPLICATE_SUFFIX) <= MAX_NAME_LENGTH:
        return name + DUPLICATE_SUFFIX
    return name[: MAX_NAME_LENGTH - len(DUPLICATE_SUFFIX)].rstrip() + DUPLICATE_SUFFIX


def touch(session: Session, workflow: Workflow) -> None:
    """Mark the workflow as changed so it sorts to the top of the list."""
    workflow.updated_at = datetime.now(UTC)
    session.flush()
