"""Inbound webhook endpoints.

A webhook URL is the only unauthenticated way into the application, so the
handler is deliberately narrow: it identifies the workflow by an unguessable
token, refuses anything that is not an active webhook workflow, and gives the
caller no information it did not already have.
"""

import json
import secrets
import uuid
from typing import Any

from fastapi import APIRouter, Request, Response, status
from sqlalchemy import select

from app.api.deps import SessionDep
from app.core.errors import AppError, NotFoundError
from app.engine.runner import execute_workflow
from app.models import ExecutionStatus, ExecutionTrigger, Workflow, WorkflowStatus
from app.nodes import get_executor
from app.schemas.execution import ExecutionSummary

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

WEBHOOK_TRIGGER_TYPE = "webhook_trigger"
#: Request bodies above this size are refused rather than stored.
MAX_BODY_BYTES = 128 * 1024
#: Headers that are safe to expose to a workflow.
FORWARDED_HEADERS = frozenset(
    {"content-type", "user-agent", "x-request-id", "x-github-event", "x-event-name"}
)


class WebhookNotActiveError(AppError):
    """The workflow exists but is not accepting webhook calls."""

    status_code = status.HTTP_409_CONFLICT
    code = "webhook_inactive"


@router.post("/{workflow_id}/{token}", status_code=status.HTTP_202_ACCEPTED)
@router.put("/{workflow_id}/{token}", status_code=status.HTTP_202_ACCEPTED)
@router.get("/{workflow_id}/{token}", status_code=status.HTTP_202_ACCEPTED)
async def receive_webhook(
    workflow_id: uuid.UUID,
    token: str,
    request: Request,
    session: SessionDep,
    response: Response,
) -> dict[str, Any]:
    """Run the workflow this webhook belongs to.

    Returns only the execution id and status: the caller is not authenticated,
    so it must not learn the shape of the workflow or the data it produced.
    """
    workflow = _resolve_workflow(session, workflow_id, token)
    trigger_node = _webhook_trigger(workflow)

    allowed = str(trigger_node.configuration.get("allowed_method", "POST")).upper()
    if request.method != allowed:
        raise WebhookNotActiveError(f"This webhook accepts {allowed} requests.")

    payload = await _read_payload(request)
    execution = await execute_workflow(
        session,
        workflow,
        trigger=ExecutionTrigger.WEBHOOK,
        trigger_payload=payload,
    )

    if execution.status is ExecutionStatus.FAILED:
        response.status_code = status.HTTP_502_BAD_GATEWAY

    summary = ExecutionSummary.model_validate(execution)
    return {"execution_id": str(summary.id), "status": summary.status.value}


def _resolve_workflow(session: SessionDep, workflow_id: uuid.UUID, token: str) -> Workflow:
    """Find the workflow, comparing the token in constant time."""
    workflow = session.scalar(select(Workflow).where(Workflow.id == workflow_id))

    # The same error covers an unknown id, a wrong token and a workflow with no
    # webhook trigger, so probing tells an attacker nothing.
    if workflow is None or not secrets.compare_digest(workflow.webhook_token, token):
        raise NotFoundError("No webhook is registered at this address.")

    if workflow.status is not WorkflowStatus.ACTIVE:
        raise WebhookNotActiveError(
            "This workflow is not active. Activate it before sending webhooks."
        )

    return workflow


def _webhook_trigger(workflow: Workflow) -> Any:
    for node in workflow.nodes:
        if node.node_type == WEBHOOK_TRIGGER_TYPE:
            get_executor(node.node_type)  # ensures the type is still installed
            return node
    raise NotFoundError("No webhook is registered at this address.")


async def _read_payload(request: Request) -> dict[str, Any]:
    """Build the trigger payload from the request, without trusting its size."""
    body = await request.body()
    if len(body) > MAX_BODY_BYTES:
        raise WebhookNotActiveError("The request body is too large.")

    parsed: Any = None
    if body:
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = body.decode("utf-8", errors="replace")

    return {
        "method": request.method,
        "headers": {
            key: value for key, value in request.headers.items() if key.lower() in FORWARDED_HEADERS
        },
        "query": dict(request.query_params),
        "body": parsed,
    }
