"""Workflow request and response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.enums import WorkflowStatus
from app.schemas.common import ORMModel

NAME_MAX_LENGTH = 120
DESCRIPTION_MAX_LENGTH = 2000


def _clean_name(value: str) -> str:
    cleaned = " ".join(value.split())
    if not cleaned:
        raise ValueError("Name cannot be blank.")
    return cleaned


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH)
    description: str = Field(default="", max_length=DESCRIPTION_MAX_LENGTH)

    _validate_name = field_validator("name")(_clean_name)


class WorkflowUpdate(BaseModel):
    """Partial update. Omitted fields are left unchanged."""

    name: str | None = Field(default=None, min_length=1, max_length=NAME_MAX_LENGTH)
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    status: WorkflowStatus | None = None

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str | None) -> str | None:
        return None if value is None else _clean_name(value)


class WorkflowSummary(ORMModel):
    """List view. Deliberately excludes the graph and the webhook token."""

    id: uuid.UUID
    name: str
    description: str
    status: WorkflowStatus
    node_count: int = 0
    created_at: datetime
    updated_at: datetime


class WorkflowDetail(WorkflowSummary):
    """Single workflow view, including the owner-only webhook details."""

    webhook_path: str
    #: Present only so the owner can copy the callable URL.
    webhook_token: str
