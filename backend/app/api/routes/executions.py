"""Starting, listing and inspecting workflow runs."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, SessionDep
from app.engine.runner import execute_workflow
from app.models import Execution, ExecutionStatus, ExecutionTrigger
from app.schemas.common import Page
from app.schemas.execution import ExecutionDetail, ExecutionSummary, RunRequest
from app.services import executions as service
from app.services import workflows as workflow_service

router = APIRouter(tags=["executions"])

MAX_PAGE_SIZE = 100


def _to_summary(execution: Execution, workflow_name: str) -> ExecutionSummary:
    return ExecutionSummary.model_validate(execution).model_copy(
        update={"workflow_name": workflow_name}
    )


def _to_detail(execution: Execution, workflow_name: str) -> ExecutionDetail:
    return ExecutionDetail.model_validate(execution).model_copy(
        update={"workflow_name": workflow_name}
    )


@router.post(
    "/workflows/{workflow_id}/run",
    response_model=ExecutionDetail,
    status_code=status.HTTP_201_CREATED,
)
async def run_workflow(
    workflow_id: uuid.UUID,
    payload: RunRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> ExecutionDetail:
    """Run a workflow once and return the completed run.

    Runs are synchronous, so the response already contains every node result.
    """
    workflow = workflow_service.get_workflow(session, current_user, workflow_id)
    execution = await execute_workflow(
        session,
        workflow,
        trigger=ExecutionTrigger.MANUAL,
        trigger_payload=payload.payload,
    )
    return _to_detail(execution, workflow.name)


@router.get("/executions", response_model=Page[ExecutionSummary])
def list_executions(
    session: SessionDep,
    current_user: CurrentUser,
    workflow_id: Annotated[uuid.UUID | None, Query()] = None,
    execution_status: Annotated[ExecutionStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[ExecutionSummary]:
    """List runs across every workflow the user owns, newest first."""
    result = service.list_executions(
        session,
        current_user,
        workflow_id=workflow_id,
        status=execution_status,
        limit=limit,
        offset=offset,
    )
    return Page(
        items=[
            _to_summary(execution, result.workflow_names.get(execution.workflow_id, ""))
            for execution in result.executions
        ],
        total=result.total,
        limit=limit,
        offset=offset,
    )


@router.get("/executions/{execution_id}", response_model=ExecutionDetail)
def read_execution(
    execution_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> ExecutionDetail:
    """Return one run with the input, output and timing of every node."""
    execution = service.get_execution(session, current_user, execution_id)
    names = service.workflow_names(session, [execution.workflow_id])
    return _to_detail(execution, names.get(execution.workflow_id, ""))


@router.post(
    "/executions/{execution_id}/retry",
    response_model=ExecutionDetail,
    status_code=status.HTTP_201_CREATED,
)
async def retry_execution(
    execution_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> ExecutionDetail:
    """Run the workflow again with the original trigger data.

    The original run is left untouched; the new run records what it was a
    retry of, so the history stays complete.
    """
    original = service.get_execution(session, current_user, execution_id)
    workflow = workflow_service.get_workflow(session, current_user, original.workflow_id)

    execution = await execute_workflow(
        session,
        workflow,
        trigger=ExecutionTrigger.RETRY,
        trigger_payload=original.trigger_payload,
        retry_of=original,
    )
    return _to_detail(execution, workflow.name)
