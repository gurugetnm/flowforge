"""The node abstraction.

Adding a node type means writing one `NodeExecutor` subclass and registering
it. Everything else — the palette in the editor, the configuration form, graph
validation and execution — is driven from what the class declares, so no other
module needs to know the new type exists.
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, ClassVar, Self, cast

from pydantic import BaseModel, ValidationError

from app.nodes.expressions import ExpressionError, render_value

#: The default output every non-branching node emits on.
DEFAULT_OUTPUT = "out"
#: The single input handle nodes accept connections on.
DEFAULT_INPUT = "in"


class NodeCategory(StrEnum):
    TRIGGER = "trigger"
    ACTION = "action"
    LOGIC = "logic"
    DATA = "data"


class Control(StrEnum):
    """How the editor renders a configuration field."""

    TEXT = "text"
    TEXTAREA = "textarea"
    NUMBER = "number"
    BOOLEAN = "boolean"
    SELECT = "select"
    JSON = "json"
    KEY_VALUE = "key_value"
    CODE = "code"


class NodeConfigError(ValueError):
    """A node's configuration is missing or malformed.

    ``field_errors`` maps a configuration key to the problems with it, so the
    editor can highlight the offending input rather than the whole node.
    """

    def __init__(self, message: str, field_errors: dict[str, list[str]] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.field_errors = field_errors or {}


class NodeExecutionError(RuntimeError):
    """A node failed while running. The message is shown in the run log."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


@dataclass(frozen=True, slots=True)
class Option:
    value: str
    label: str


@dataclass(frozen=True, slots=True)
class Output:
    """One outgoing connection point on a node."""

    key: str
    label: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class FieldSpec:
    """Everything the editor needs to render one configuration input."""

    key: str
    label: str
    control: Control
    required: bool = False
    default: Any = None
    help_text: str = ""
    placeholder: str = ""
    options: tuple[Option, ...] = ()
    #: Whether `{{ }}` expressions are resolved in this field at run time.
    supports_expressions: bool = False
    #: Only show this field when another field has one of these values.
    depends_on: str | None = None
    depends_on_values: tuple[str, ...] = ()


@dataclass(slots=True)
class NodeContext:
    """Run-time information handed to a node.

    ``variables`` is shared across the whole run: a Set Variable node writes to
    it and every later node reads from it.
    """

    input: dict[str, Any]
    variables: dict[str, Any]
    trigger: dict[str, Any]
    #: Outputs of nodes that already ran, keyed by node label.
    nodes: dict[str, Any] = field(default_factory=dict)
    logs: list[str] = field(default_factory=list)

    def log(self, message: str) -> None:
        self.logs.append(message)

    def expression_scope(self) -> dict[str, Any]:
        return {
            "input": self.input,
            "vars": self.variables,
            "trigger": self.trigger,
            "nodes": self.nodes,
        }

    def render(self, value: Any) -> Any:
        """Resolve `{{ }}` expressions in ``value`` against this context."""
        try:
            return render_value(value, self.expression_scope())
        except ExpressionError as error:
            raise NodeExecutionError(str(error)) from error


@dataclass(frozen=True, slots=True)
class NodeResult:
    """What a node produced, and where the run should go next."""

    output: dict[str, Any] = field(default_factory=dict)
    #: Output handles to follow. ``None`` means "every declared output".
    branches: tuple[str, ...] | None = None
    logs: tuple[str, ...] = ()

    @classmethod
    def of(cls, output: dict[str, Any] | None = None, **kwargs: Any) -> Self:
        return cls(output=output or {}, **kwargs)


class EmptyConfig(BaseModel):
    """Configuration model for nodes that take no settings."""


class NodeExecutor[ConfigT: BaseModel](ABC):
    """Base class for every node type."""

    #: Stable identifier persisted in `workflow_nodes.node_type`.
    node_type: ClassVar[str]
    name: ClassVar[str]
    category: ClassVar[NodeCategory]
    description: ClassVar[str] = ""
    #: Whether this node can receive an incoming connection.
    accepts_input: ClassVar[bool] = True
    outputs: ClassVar[tuple[Output, ...]] = (Output(DEFAULT_OUTPUT, "Output"),)
    fields: ClassVar[tuple[FieldSpec, ...]] = ()

    #: Pydantic model validating this node's `configuration` JSON.
    config_model: ClassVar[type[BaseModel]] = EmptyConfig

    @property
    def is_trigger(self) -> bool:
        return self.category is NodeCategory.TRIGGER

    def validate_config(self, configuration: dict[str, Any]) -> ConfigT:
        """Parse stored configuration, raising `NodeConfigError` if unusable.

        Fields that support expressions may hold a `{{ }}` placeholder that
        only resolves at run time, so those are checked for shape rather than
        for a concrete value.
        """
        try:
            return cast("ConfigT", self.config_model.model_validate(configuration))
        except ValidationError as error:
            field_errors: dict[str, list[str]] = {}
            for issue in error.errors():
                key = ".".join(str(part) for part in issue["loc"]) or "_"
                field_errors.setdefault(key, []).append(_readable(issue))
            first = next(iter(field_errors.items()))
            raise NodeConfigError(
                f"{self.name}: {first[1][0]}" if first[0] == "_" else f"{first[0]}: {first[1][0]}",
                field_errors,
            ) from error

    @abstractmethod
    async def execute(self, config: ConfigT, context: NodeContext) -> NodeResult:
        """Run the node and return its output."""

    def outputs_for(self, configuration: dict[str, Any]) -> tuple[Output, ...]:
        """The output handles this node exposes.

        Most nodes have a fixed set; Switch derives one handle per case, so the
        editor and the validator both ask here rather than reading `outputs`.
        """
        return self.outputs

    def default_configuration(self) -> dict[str, Any]:
        """Configuration a freshly dropped node starts with."""
        return {spec.key: spec.default for spec in self.fields if spec.default is not None}


def _readable(issue: Mapping[str, Any]) -> str:
    """Turn a Pydantic error into something worth showing a developer."""
    message = str(issue.get("msg", "is invalid"))
    if issue.get("type") == "missing":
        return "This field is required."
    return message[0].upper() + message[1:] if message else "This field is invalid."
