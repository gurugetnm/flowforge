"""Workflow graph models: the workflow itself, its nodes and its edges."""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Float, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, uuid_pk
from app.models.enums import WorkflowStatus

if TYPE_CHECKING:
    from app.models.execution import Execution
    from app.models.user import User


class Workflow(TimestampMixin, Base):
    """A named, versionless automation graph owned by a single user."""

    __tablename__ = "workflows"
    __table_args__ = (Index("ix_workflows_owner_updated", "owner_id", "updated_at"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[WorkflowStatus] = mapped_column(
        String(16), default=WorkflowStatus.DRAFT, nullable=False
    )
    #: Opaque secret used to authenticate inbound webhook calls for this workflow.
    webhook_token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)

    owner: Mapped["User"] = relationship(back_populates="workflows")
    nodes: Mapped[list["WorkflowNode"]] = relationship(
        back_populates="workflow",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="WorkflowNode.created_at",
    )
    edges: Mapped[list["WorkflowEdge"]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan", passive_deletes=True
    )
    executions: Mapped[list["Execution"]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan", passive_deletes=True
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<Workflow {self.name!r} {self.status}>"


class WorkflowNode(TimestampMixin, Base):
    """A single step in a workflow graph.

    ``node_type`` is resolved against the node registry at validation and
    execution time; ``configuration`` holds the type specific settings and is
    validated by that node type's configuration schema.
    """

    __tablename__ = "workflow_nodes"

    id: Mapped[uuid.UUID] = uuid_pk()
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True
    )
    node_type: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    configuration: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    position_x: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    position_y: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    workflow: Mapped["Workflow"] = relationship(back_populates="nodes")


class WorkflowEdge(TimestampMixin, Base):
    """A directed connection between two nodes of the same workflow.

    ``source_handle`` selects which output of the source node the edge is
    attached to, which is how branching nodes route their result.
    """

    __tablename__ = "workflow_edges"
    __table_args__ = (
        UniqueConstraint(
            "source_node_id",
            "target_node_id",
            "source_handle",
            "target_handle",
            name="uq_workflow_edges_connection",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_node_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_handle: Mapped[str] = mapped_column(String(64), default="out", nullable=False)
    target_handle: Mapped[str] = mapped_column(String(64), default="in", nullable=False)

    workflow: Mapped["Workflow"] = relationship(back_populates="edges")
