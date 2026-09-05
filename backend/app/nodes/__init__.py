"""The node system.

Importing this package registers every built-in node type, so anything that
needs the registry only has to ``import app.nodes``.
"""

from app.nodes import actions, data, logic, triggers  # noqa: F401 - imported for registration
from app.nodes.base import (
    DEFAULT_INPUT,
    DEFAULT_OUTPUT,
    Control,
    FieldSpec,
    NodeCategory,
    NodeConfigError,
    NodeContext,
    NodeExecutionError,
    NodeExecutor,
    NodeResult,
    Option,
    Output,
)
from app.nodes.registry import (
    UnknownNodeTypeError,
    all_executors,
    get_executor,
    has_node_type,
    trigger_types,
)

__all__ = [
    "DEFAULT_INPUT",
    "DEFAULT_OUTPUT",
    "Control",
    "FieldSpec",
    "NodeCategory",
    "NodeConfigError",
    "NodeContext",
    "NodeExecutionError",
    "NodeExecutor",
    "NodeResult",
    "Option",
    "Output",
    "UnknownNodeTypeError",
    "all_executors",
    "get_executor",
    "has_node_type",
    "trigger_types",
]
