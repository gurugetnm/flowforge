"""Trigger nodes: where a run starts."""

from typing import Any, Literal

from pydantic import BaseModel

from app.nodes.base import (
    Control,
    EmptyConfig,
    NodeCategory,
    NodeContext,
    NodeExecutor,
    NodeResult,
    Option,
)
from app.nodes.fields import config_field, describe
from app.nodes.registry import register


@register
class ManualTriggerExecutor(NodeExecutor[EmptyConfig]):
    """Starts a run when someone presses Run in the editor."""

    node_type = "manual_trigger"
    name = "Manual Trigger"
    category = NodeCategory.TRIGGER
    description = "Starts the workflow when you run it by hand."
    accepts_input = False
    config_model = EmptyConfig

    async def execute(self, config: EmptyConfig, context: NodeContext) -> NodeResult:
        return NodeResult.of({"payload": context.trigger})


WEBHOOK_METHODS = ("POST", "GET", "PUT")


class WebhookTriggerConfig(BaseModel):
    allowed_method: Literal["POST", "GET", "PUT"] = config_field(
        label="Accepted method",
        control=Control.SELECT,
        default="POST",
        help_text="Requests using any other method are rejected.",
        options=tuple(Option(method, method) for method in WEBHOOK_METHODS),
    )


@register
class WebhookTriggerExecutor(NodeExecutor[WebhookTriggerConfig]):
    """Starts a run when the workflow's webhook endpoint is called."""

    node_type = "webhook_trigger"
    name = "Webhook Trigger"
    category = NodeCategory.TRIGGER
    description = "Starts the workflow when its webhook URL receives a request."
    accepts_input = False
    config_model = WebhookTriggerConfig
    fields = describe(WebhookTriggerConfig)

    async def execute(self, config: WebhookTriggerConfig, context: NodeContext) -> NodeResult:
        payload: dict[str, Any] = dict(context.trigger)
        context.log(f"Webhook received {payload.get('method', 'a request')}")
        return NodeResult.of(payload)
