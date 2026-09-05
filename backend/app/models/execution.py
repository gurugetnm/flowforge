"""Execution records: one row per run, plus one row per node within that run."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, EnumString, TimestampMixin, uuid_pk
from app.models.enums import ExecutionStatus, ExecutionTrigger, NodeRunStatus

if TYPE_CHECKING:
    from app.models.workflow import Workflow


class Execution(TimestampMixin, Base):
    """A single run of a workflow.

    Execution records are append only: retrying a failed run creates a new
    execution that points back at the original through ``retry_of_id``.
    """

    __tablename__ = "executions"
    __table_args__ = (Index("ix_executions_workflow_started", "workflow_id", "started_at"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[ExecutionStatus] = mapped_column(
        EnumString(ExecutionStatus), default=ExecutionStatus.PENDING, nullable=False, index=True
    )
    trigger: Mapped[ExecutionTrigger] = mapped_column(
        EnumString(ExecutionTrigger), default=ExecutionTrigger.MANUAL, nullable=False
    )
    #: Payload handed to the trigger node, e.g. a webhook request body.
    trigger_payload: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    #: Variables accumulated by Set Variable nodes over the run.
    variables: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    retry_of_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("executions.id", ondelete="SET NULL"), nullable=True, index=True
    )

    workflow: Mapped["Workflow"] = relationship(back_populates="executions")
    node_runs: Mapped[list["ExecutionNode"]] = relationship(
        back_populates="execution",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ExecutionNode.sequence",
    )
    retry_of: Mapped["Execution | None"] = relationship(remote_side=[id])

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<Execution {self.id} {self.status}>"


class ExecutionNode(TimestampMixin, Base):
    """The result of one node inside one execution.

    The node's type and label are copied in so the run stays readable even
    after the workflow graph has been edited or the node deleted.
    """

    __tablename__ = "execution_nodes"
    __table_args__ = (Index("ix_execution_nodes_execution_sequence", "execution_id", "sequence"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    execution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("executions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    node_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workflow_nodes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    node_type: Mapped[str] = mapped_column(String(64), nullable=False)
    node_label: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[NodeRunStatus] = mapped_column(
        EnumString(NodeRunStatus), default=NodeRunStatus.PENDING, nullable=False
    )
    #: Position of the node in the resolved execution order, starting at 0.
    sequence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    input: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    output: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    logs: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    execution: Mapped["Execution"] = relationship(back_populates="node_runs")
