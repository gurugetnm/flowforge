"""Data nodes: introduce values into a run, or carry them forward."""

import json
from typing import Any

from pydantic import BaseModel, field_validator

from app.nodes.base import (
    Control,
    NodeCategory,
    NodeContext,
    NodeExecutor,
    NodeResult,
)
from app.nodes.fields import config_field, describe
from app.nodes.registry import register

MAX_VARIABLE_NAME_LENGTH = 64


class JsonInputConfig(BaseModel):
    payload: str = config_field(
        label="JSON",
        control=Control.JSON,
        default="{}",
        help_text="A JSON document made available to the nodes that follow.",
        placeholder='{"name": "example"}',
    )

    @field_validator("payload")
    @classmethod
    def _must_be_valid_json(cls, value: str) -> str:
        try:
            parsed = json.loads(value or "{}")
        except json.JSONDecodeError as error:
            raise ValueError(
                f"This is not valid JSON ({error.msg} at line {error.lineno})."
            ) from None
        if not isinstance(parsed, dict | list):
            raise ValueError("The value must be a JSON object or array.")
        return value


@register
class JsonInputExecutor(NodeExecutor[JsonInputConfig]):
    """Emits a fixed JSON document."""

    node_type = "json_input"
    name = "JSON Input"
    category = NodeCategory.DATA
    description = "Provides a fixed JSON document to the nodes downstream."
    config_model = JsonInputConfig
    fields = describe(JsonInputConfig)

    async def execute(self, config: JsonInputConfig, context: NodeContext) -> NodeResult:
        parsed = json.loads(config.payload or "{}")
        return NodeResult.of(parsed if isinstance(parsed, dict) else {"items": parsed})


class SetVariableConfig(BaseModel):
    name: str = config_field(
        label="Variable name",
        control=Control.TEXT,
        help_text="Read it later with {{ vars.<name> }}.",
        placeholder="api_token",
        min_length=1,
        max_length=MAX_VARIABLE_NAME_LENGTH,
    )
    value: str = config_field(
        label="Value",
        control=Control.TEXTAREA,
        default="",
        help_text="Supports expressions, for example {{ input.id }}.",
        supports_expressions=True,
    )

    @field_validator("name")
    @classmethod
    def _must_be_an_identifier(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned.isidentifier():
            raise ValueError("Use letters, digits and underscores, starting with a letter.")
        return cleaned


@register
class SetVariableExecutor(NodeExecutor[SetVariableConfig]):
    """Stores a value under a name for the rest of the run."""

    node_type = "set_variable"
    name = "Set Variable"
    category = NodeCategory.DATA
    description = "Stores a value that later nodes can read with {{ vars.name }}."
    config_model = SetVariableConfig
    fields = describe(SetVariableConfig)

    async def execute(self, config: SetVariableConfig, context: NodeContext) -> NodeResult:
        value = context.render(config.value)
        context.variables[config.name] = value
        context.log(f"Set {config.name}")
        return NodeResult.of({**context.input, config.name: value})


class JsonTransformConfig(BaseModel):
    template: str = config_field(
        label="Output template",
        control=Control.JSON,
        default="{}",
        help_text=(
            "A JSON object describing the output. String values may use "
            "expressions such as {{ input.user.email }}."
        ),
        placeholder='{"email": "{{ input.user.email }}"}',
        supports_expressions=True,
    )

    @field_validator("template")
    @classmethod
    def _must_be_valid_json(cls, value: str) -> str:
        try:
            parsed = json.loads(value or "{}")
        except json.JSONDecodeError as error:
            raise ValueError(
                f"This is not valid JSON ({error.msg} at line {error.lineno})."
            ) from None
        if not isinstance(parsed, dict | list):
            raise ValueError("The template must be a JSON object or array.")
        return value


@register
class JsonTransformExecutor(NodeExecutor[JsonTransformConfig]):
    """Reshapes the incoming data into a new JSON document."""

    node_type = "json_transform"
    name = "JSON Transform"
    category = NodeCategory.DATA
    description = "Builds a new JSON document from the incoming data."
    config_model = JsonTransformConfig
    fields = describe(JsonTransformConfig)

    async def execute(self, config: JsonTransformConfig, context: NodeContext) -> NodeResult:
        template: Any = json.loads(config.template or "{}")
        rendered = context.render(template)
        if not isinstance(rendered, dict):
            return NodeResult.of({"items": rendered})
        return NodeResult.of(rendered)
