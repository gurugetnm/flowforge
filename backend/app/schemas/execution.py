"""Execution request and response schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import ExecutionStatus, ExecutionTrigger, NodeRunStatus
from app.schemas.common import ORMModel

MAX_TRIGGER_PAYLOAD_KEYS = 100


class RunRequest(BaseModel):
    """Optional data handed to the trigger node."""

    payload: dict[str, Any] = Field(default_factory=dict)


class ExecutionNodeResponse(ORMModel):
    """One node's result inside a run."""

    id: uuid.UUID
    node_id: uuid.UUID | None
    node_type: str
    node_label: str
    status: NodeRunStatus
    sequence: int
    input: dict[str, Any]
    output: dict[str, Any]
    logs: dict[str, Any]
    error: str | None
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None


class ExecutionSummary(ORMModel):
    """List view of a run."""

    id: uuid.UUID
    workflow_id: uuid.UUID
    workflow_name: str = ""
    status: ExecutionStatus
    trigger: ExecutionTrigger
    error: str | None
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    retry_of_id: uuid.UUID | None
    created_at: datetime


class ExecutionDetail(ExecutionSummary):
    """Full run, including every node result."""

    trigger_payload: dict[str, Any]
    variables: dict[str, Any]
    node_runs: list[ExecutionNodeResponse]
