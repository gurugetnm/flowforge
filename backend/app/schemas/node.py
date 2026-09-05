"""Schemas describing the installed node types to the editor."""

from typing import Any

from pydantic import BaseModel

from app.nodes import FieldSpec, NodeCategory
from app.nodes.registry import AnyExecutor


class OptionSchema(BaseModel):
    value: str
    label: str


class FieldSchema(BaseModel):
    """One configuration input, as the editor should render it."""

    key: str
    label: str
    control: str
    required: bool
    default: Any = None
    help_text: str = ""
    placeholder: str = ""
    options: list[OptionSchema] = []
    supports_expressions: bool = False
    depends_on: str | None = None
    depends_on_values: list[str] = []

    @classmethod
    def from_spec(cls, spec: FieldSpec) -> "FieldSchema":
        return cls(
            key=spec.key,
            label=spec.label,
            control=spec.control.value,
            required=spec.required,
            default=spec.default,
            help_text=spec.help_text,
            placeholder=spec.placeholder,
            options=[OptionSchema(value=o.value, label=o.label) for o in spec.options],
            supports_expressions=spec.supports_expressions,
            depends_on=spec.depends_on,
            depends_on_values=list(spec.depends_on_values),
        )


class OutputSchema(BaseModel):
    key: str
    label: str
    description: str = ""


class NodeTypeSchema(BaseModel):
    """A node type as it appears in the palette and configuration panel."""

    type: str
    name: str
    category: NodeCategory
    description: str
    accepts_input: bool
    is_trigger: bool
    outputs: list[OutputSchema]
    fields: list[FieldSchema]
    default_configuration: dict[str, Any]

    @classmethod
    def from_executor(cls, executor: AnyExecutor) -> "NodeTypeSchema":
        return cls(
            type=executor.node_type,
            name=executor.name,
            category=executor.category,
            description=executor.description,
            accepts_input=executor.accepts_input,
            is_trigger=executor.is_trigger,
            outputs=[
                OutputSchema(key=o.key, label=o.label, description=o.description)
                for o in executor.outputs
            ],
            fields=[FieldSchema.from_spec(spec) for spec in executor.fields],
            default_configuration=executor.default_configuration(),
        )
