"""Reading and starting workflow runs."""

import uuid
from dataclasses import dataclass

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import NotFoundError
from app.models import Execution, ExecutionStatus, User, Workflow


@dataclass(frozen=True, slots=True)
class ExecutionListResult:
    executions: list[Execution]
    workflow_names: dict[uuid.UUID, str]
    total: int


def _owned(user: User) -> Select[tuple[Execution]]:
    """Executions belonging to workflows the user owns."""
    return select(Execution).join(Workflow).where(Workflow.owner_id == user.id)


def get_execution(session: Session, user: User, execution_id: uuid.UUID) -> Execution:
    execution = session.scalar(
        _owned(user).where(Execution.id == execution_id).options(selectinload(Execution.node_runs))
    )
    if execution is None:
        raise NotFoundError("Execution not found.")
    return execution


def list_executions(
    session: Session,
    user: User,
    *,
    workflow_id: uuid.UUID | None = None,
    status: ExecutionStatus | None = None,
    limit: int = 20,
    offset: int = 0,
) -> ExecutionListResult:
    """Return a page of runs, newest first."""
    query = _owned(user)
    if workflow_id is not None:
        query = query.where(Execution.workflow_id == workflow_id)
    if status is not None:
        query = query.where(Execution.status == status)

    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    executions = list(
        session.scalars(
            query.order_by(Execution.created_at.desc(), Execution.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )

    return ExecutionListResult(
        executions=executions,
        workflow_names=workflow_names(session, [e.workflow_id for e in executions]),
        total=total,
    )


def workflow_names(session: Session, workflow_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    """Look up the names of several workflows in one query."""
    if not workflow_ids:
        return {}
    rows = (
        session.execute(
            select(Workflow.id, Workflow.name).where(Workflow.id.in_(set(workflow_ids)))
        )
        .tuples()
        .all()
    )
    return dict(rows)


def count_by_status(session: Session, user: User) -> dict[str, int]:
    """Run totals per status, for the dashboard."""
    rows = (
        session.execute(
            select(Execution.status, func.count(Execution.id))
            .join(Workflow)
            .where(Workflow.owner_id == user.id)
            .group_by(Execution.status)
        )
        .tuples()
        .all()
    )
    counts = {status.value: 0 for status in ExecutionStatus}
    counts.update({str(status): count for status, count in rows})
    return counts
