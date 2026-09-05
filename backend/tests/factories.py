"""Object factories used across the test suite."""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models import User, Workflow, WorkflowEdge, WorkflowNode


def unique_email(prefix: str = "dev") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}@flowforge.test"


def make_user(session: Session, **overrides: Any) -> User:
    user = User(
        email=overrides.pop("email", unique_email()),
        name=overrides.pop("name", "Test Developer"),
        password_hash=overrides.pop("password_hash", "not-a-real-hash"),
        **overrides,
    )
    session.add(user)
    session.flush()
    return user


def make_workflow(session: Session, owner: User, **overrides: Any) -> Workflow:
    workflow = Workflow(
        owner_id=owner.id,
        name=overrides.pop("name", "Test workflow"),
        description=overrides.pop("description", ""),
        webhook_token=overrides.pop("webhook_token", uuid.uuid4().hex),
        **overrides,
    )
    session.add(workflow)
    session.flush()
    return workflow


def make_node(
    session: Session, workflow: Workflow, node_type: str, **overrides: Any
) -> WorkflowNode:
    node = WorkflowNode(
        workflow_id=workflow.id,
        node_type=node_type,
        label=overrides.pop("label", node_type.replace("_", " ").title()),
        configuration=overrides.pop("configuration", {}),
        **overrides,
    )
    session.add(node)
    session.flush()
    return node


def connect(
    session: Session,
    source: WorkflowNode,
    target: WorkflowNode,
    source_handle: str = "out",
    target_handle: str = "in",
) -> WorkflowEdge:
    edge = WorkflowEdge(
        workflow_id=source.workflow_id,
        source_node_id=source.id,
        target_node_id=target.id,
        source_handle=source_handle,
        target_handle=target_handle,
    )
    session.add(edge)
    session.flush()
    return edge
