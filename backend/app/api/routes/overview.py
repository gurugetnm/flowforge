"""Dashboard summary."""

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import Workflow, WorkflowStatus
from app.schemas.execution import ExecutionSummary
from app.services import executions as execution_service

RECENT_EXECUTION_LIMIT = 5


class OverviewResponse(BaseModel):
    """Everything the dashboard needs, in one round trip."""

    workflow_count: int
    active_workflow_count: int
    execution_counts: dict[str, int]
    recent_executions: list[ExecutionSummary]


router = APIRouter(prefix="/overview", tags=["overview"])


@router.get("", response_model=OverviewResponse)
def read_overview(session: SessionDep, current_user: CurrentUser) -> OverviewResponse:
    workflow_count = (
        session.scalar(select(func.count(Workflow.id)).where(Workflow.owner_id == current_user.id))
        or 0
    )
    active_count = (
        session.scalar(
            select(func.count(Workflow.id)).where(
                Workflow.owner_id == current_user.id,
                Workflow.status == WorkflowStatus.ACTIVE,
            )
        )
        or 0
    )

    recent = execution_service.list_executions(session, current_user, limit=RECENT_EXECUTION_LIMIT)

    return OverviewResponse(
        workflow_count=workflow_count,
        active_workflow_count=active_count,
        execution_counts=execution_service.count_by_status(session, current_user),
        recent_executions=[
            ExecutionSummary.model_validate(execution).model_copy(
                update={"workflow_name": recent.workflow_names.get(execution.workflow_id, "")}
            )
            for execution in recent.executions
        ],
    )
