"""Workflow CRUD endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, SessionDep
from app.models import Workflow, WorkflowStatus
from app.schemas.common import Page
from app.schemas.graph import GraphUpdate, WorkflowGraph
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowDetail,
    WorkflowSummary,
    WorkflowUpdate,
)
from app.services import graph as graph_service
from app.services import workflows as service

router = APIRouter(prefix="/workflows", tags=["workflows"])

MAX_PAGE_SIZE = 100


def _to_summary(workflow: Workflow, node_count: int) -> WorkflowSummary:
    return WorkflowSummary.model_validate(workflow).model_copy(update={"node_count": node_count})


def _to_detail(workflow: Workflow) -> WorkflowDetail:
    return WorkflowDetail(
        **_to_summary(workflow, len(workflow.nodes)).model_dump(),
        webhook_path=f"/api/webhooks/{workflow.id}/{workflow.webhook_token}",
        webhook_token=workflow.webhook_token,
    )


@router.get("", response_model=Page[WorkflowSummary])
def list_workflows(
    session: SessionDep,
    current_user: CurrentUser,
    search: Annotated[str | None, Query(max_length=120)] = None,
    workflow_status: Annotated[WorkflowStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[WorkflowSummary]:
    """List the current user's workflows, most recently updated first."""
    result = service.list_workflows(
        session,
        current_user,
        search=search,
        status=workflow_status,
        limit=limit,
        offset=offset,
    )
    return Page(
        items=[_to_summary(w, result.node_counts.get(w.id, 0)) for w in result.workflows],
        total=result.total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=WorkflowSummary, status_code=status.HTTP_201_CREATED)
def create_workflow(
    payload: WorkflowCreate, session: SessionDep, current_user: CurrentUser
) -> WorkflowSummary:
    workflow = service.create_workflow(
        session, current_user, name=payload.name, description=payload.description
    )
    return _to_summary(workflow, 0)


@router.get("/{workflow_id}", response_model=WorkflowDetail)
def read_workflow(
    workflow_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> WorkflowDetail:
    workflow = service.get_workflow(session, current_user, workflow_id)
    return _to_detail(workflow)


@router.patch("/{workflow_id}", response_model=WorkflowSummary)
def update_workflow(
    workflow_id: uuid.UUID,
    payload: WorkflowUpdate,
    session: SessionDep,
    current_user: CurrentUser,
) -> WorkflowSummary:
    workflow = service.get_workflow(session, current_user, workflow_id)
    service.update_workflow(
        session,
        workflow,
        name=payload.name,
        description=payload.description,
        status=payload.status,
    )
    return _to_summary(workflow, len(workflow.nodes))


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow(workflow_id: uuid.UUID, session: SessionDep, current_user: CurrentUser) -> None:
    workflow = service.get_workflow(session, current_user, workflow_id)
    service.delete_workflow(session, workflow)


@router.post(
    "/{workflow_id}/duplicate",
    response_model=WorkflowSummary,
    status_code=status.HTTP_201_CREATED,
)
def duplicate_workflow(
    workflow_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> WorkflowSummary:
    """Copy a workflow's graph into a new draft workflow."""
    workflow = service.get_workflow(session, current_user, workflow_id)
    copy = service.duplicate_workflow(session, current_user, workflow)
    return _to_summary(copy, len(copy.nodes))


@router.get("/{workflow_id}/graph", response_model=WorkflowGraph)
def read_graph(
    workflow_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> WorkflowGraph:
    """Return the workflow's nodes and connections."""
    workflow = service.get_workflow(session, current_user, workflow_id)
    return graph_service.read_graph(workflow)


@router.put("/{workflow_id}/graph", response_model=WorkflowGraph)
def replace_graph(
    workflow_id: uuid.UUID,
    payload: GraphUpdate,
    session: SessionDep,
    current_user: CurrentUser,
) -> WorkflowGraph:
    """Replace the workflow's graph with the editor's current state.

    The whole graph is sent at once so a save is atomic: the stored graph is
    never a partially applied version of what the editor showed.
    """
    workflow = service.get_workflow(session, current_user, workflow_id)
    saved = graph_service.replace_graph(session, workflow, payload)
    service.touch(session, workflow)
    return saved
