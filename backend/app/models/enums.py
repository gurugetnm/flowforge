"""Enumerations shared by the ORM models and the API schemas."""

from enum import StrEnum


class WorkflowStatus(StrEnum):
    """Whether a workflow may be triggered."""

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class ExecutionStatus(StrEnum):
    """Lifecycle of a single workflow run."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        return self in {ExecutionStatus.SUCCEEDED, ExecutionStatus.FAILED}


class NodeRunStatus(StrEnum):
    """Outcome of a single node within a run."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    #: The node was never reached, because an upstream branch was not taken.
    SKIPPED = "skipped"


class ExecutionTrigger(StrEnum):
    """What caused a run to start."""

    MANUAL = "manual"
    WEBHOOK = "webhook"
    RETRY = "retry"
