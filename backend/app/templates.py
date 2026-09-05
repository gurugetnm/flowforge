"""Starter workflows.

Each template is a complete, valid graph so a new user can run something
useful immediately and then edit it, rather than starting from a blank canvas.
Node ids are generated when a template is instantiated, so two workflows
created from the same template share nothing.
"""

import uuid
from dataclasses import dataclass, field
from typing import Any

from app.schemas.graph import GraphEdge, GraphNode, GraphUpdate, Position

#: Horizontal and vertical spacing used to lay templates out on the canvas.
COLUMN_WIDTH = 280
ROW_HEIGHT = 150


@dataclass(frozen=True, slots=True)
class TemplateNode:
    """A node in a template, addressed by a readable key rather than an id."""

    key: str
    type: str
    label: str
    configuration: dict[str, Any] = field(default_factory=dict)
    column: int = 0
    row: int = 0


@dataclass(frozen=True, slots=True)
class TemplateEdge:
    source: str
    target: str
    source_handle: str = "out"


@dataclass(frozen=True, slots=True)
class WorkflowTemplate:
    id: str
    name: str
    description: str
    nodes: tuple[TemplateNode, ...]
    edges: tuple[TemplateEdge, ...]

    def build(self) -> GraphUpdate:
        """Turn the template into a graph with freshly generated ids."""
        ids = {node.key: uuid.uuid4() for node in self.nodes}

        return GraphUpdate(
            nodes=[
                GraphNode(
                    id=ids[node.key],
                    type=node.type,
                    label=node.label,
                    configuration=dict(node.configuration),
                    position=Position(x=node.column * COLUMN_WIDTH, y=node.row * ROW_HEIGHT),
                )
                for node in self.nodes
            ],
            edges=[
                GraphEdge(
                    id=uuid.uuid4(),
                    source=ids[edge.source],
                    target=ids[edge.target],
                    source_handle=edge.source_handle,
                )
                for edge in self.edges
            ],
        )


TEMPLATES: tuple[WorkflowTemplate, ...] = (
    WorkflowTemplate(
        id="webhook-to-api",
        name="Webhook to API",
        description="Receive a webhook, forward it to an HTTP API, and log the response.",
        nodes=(
            TemplateNode("trigger", "webhook_trigger", "On webhook", {"allowed_method": "POST"}),
            TemplateNode(
                "request",
                "http_request",
                "Forward to API",
                {
                    "method": "POST",
                    "url": "https://httpbin.org/post",
                    "headers": {"Content-Type": "application/json"},
                    "body": '{"received": "{{ trigger.body }}"}',
                    "timeout_seconds": 10,
                },
                column=1,
            ),
            TemplateNode(
                "log",
                "log",
                "Log the response",
                {"message": "Forwarded, API replied {{ input.status_code }}", "level": "info"},
                column=2,
            ),
        ),
        edges=(TemplateEdge("trigger", "request"), TemplateEdge("request", "log")),
    ),
    WorkflowTemplate(
        id="webhook-conditional-request",
        name="Conditional webhook handler",
        description="Branch on the webhook payload and only call the API when it matters.",
        nodes=(
            TemplateNode("trigger", "webhook_trigger", "On webhook", {"allowed_method": "POST"}),
            TemplateNode(
                "condition",
                "condition",
                "Is it an open event?",
                {"left": "{{ trigger.body.action }}", "operator": "equals", "right": "opened"},
                column=1,
            ),
            TemplateNode(
                "request",
                "http_request",
                "Notify the API",
                {
                    "method": "POST",
                    "url": "https://httpbin.org/post",
                    "headers": {"Content-Type": "application/json"},
                    "body": '{"action": "{{ trigger.body.action }}"}',
                    "timeout_seconds": 10,
                },
                column=2,
            ),
            TemplateNode(
                "ignored",
                "log",
                "Ignore it",
                {"message": "Ignored {{ trigger.body.action }}", "level": "debug"},
                column=2,
                row=1,
            ),
        ),
        edges=(
            TemplateEdge("trigger", "condition"),
            TemplateEdge("condition", "request", source_handle="true"),
            TemplateEdge("condition", "ignored", source_handle="false"),
        ),
    ),
    WorkflowTemplate(
        id="json-transform-pipeline",
        name="Transform and log JSON",
        description="A self-contained example: fixed JSON in, reshaped and logged out.",
        nodes=(
            TemplateNode("trigger", "manual_trigger", "Run manually"),
            TemplateNode(
                "input",
                "json_input",
                "Sample payload",
                {"payload": '{"user": {"id": 42, "name": "Ada", "email": "ada@example.com"}}'},
                column=1,
            ),
            TemplateNode(
                "transform",
                "json_transform",
                "Reshape",
                {
                    "template": (
                        '{"id": "{{ input.user.id }}", "contact": "{{ input.user.email }}"}'
                    )
                },
                column=2,
            ),
            TemplateNode(
                "log",
                "log",
                "Log the result",
                {"message": "Contact for {{ input.id }} is {{ input.contact }}", "level": "info"},
                column=3,
            ),
        ),
        edges=(
            TemplateEdge("trigger", "input"),
            TemplateEdge("input", "transform"),
            TemplateEdge("transform", "log"),
        ),
    ),
)

TEMPLATES_BY_ID = {template.id: template for template in TEMPLATES}


def get_template(template_id: str) -> WorkflowTemplate | None:
    return TEMPLATES_BY_ID.get(template_id)
