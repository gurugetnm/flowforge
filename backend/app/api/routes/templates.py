"""Starter templates and creating a workflow from one."""

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, SessionDep
from app.core.errors import NotFoundError
from app.schemas.workflow import NAME_MAX_LENGTH, WorkflowSummary
from app.services import graph as graph_service
from app.services import workflows as workflow_service
from app.templates import TEMPLATES, get_template

router = APIRouter(prefix="/templates", tags=["templates"])


class TemplateSummary(BaseModel):
    id: str
    name: str
    description: str
    node_count: int
    node_types: list[str]


class CreateFromTemplateRequest(BaseModel):
    """Optionally override the name the new workflow gets."""

    name: str | None = Field(default=None, min_length=1, max_length=NAME_MAX_LENGTH)


@router.get("", response_model=list[TemplateSummary])
def list_templates(current_user: CurrentUser) -> list[TemplateSummary]:
    """Describe the starter workflows a user can begin from."""
    return [
        TemplateSummary(
            id=template.id,
            name=template.name,
            description=template.description,
            node_count=len(template.nodes),
            node_types=[node.type for node in template.nodes],
        )
        for template in TEMPLATES
    ]


@router.post(
    "/{template_id}/create",
    response_model=WorkflowSummary,
    status_code=status.HTTP_201_CREATED,
)
def create_from_template(
    template_id: str,
    payload: CreateFromTemplateRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> WorkflowSummary:
    """Create a new draft workflow containing the template's graph."""
    template = get_template(template_id)
    if template is None:
        raise NotFoundError("Template not found.")

    workflow = workflow_service.create_workflow(
        session,
        current_user,
        name=payload.name or template.name,
        description=template.description,
    )
    graph_service.replace_graph(session, workflow, template.build())

    return WorkflowSummary.model_validate(workflow).model_copy(
        update={"node_count": len(template.nodes)}
    )
