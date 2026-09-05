"""The node type registry.

A single instance of every executor is kept, since executors are stateless and
all run-time data arrives through `NodeContext`.
"""

from typing import Any

from app.nodes.base import NodeCategory, NodeExecutor

#: Executors are stored without their configuration type, which only matters
#: inside the executor itself.
AnyExecutor = NodeExecutor[Any]

_REGISTRY: dict[str, AnyExecutor] = {}


class UnknownNodeTypeError(KeyError):
    """Raised when a workflow references a node type that is not installed."""

    def __init__(self, node_type: str) -> None:
        super().__init__(node_type)
        self.node_type = node_type

    def __str__(self) -> str:
        return f"Unknown node type {self.node_type!r}."


def register(executor_class: type[AnyExecutor]) -> type[AnyExecutor]:
    """Class decorator adding an executor to the registry."""
    executor = executor_class()
    if executor.node_type in _REGISTRY:
        raise ValueError(f"Node type {executor.node_type!r} is already registered.")
    _REGISTRY[executor.node_type] = executor
    return executor_class


def get_executor(node_type: str) -> AnyExecutor:
    try:
        return _REGISTRY[node_type]
    except KeyError:
        raise UnknownNodeTypeError(node_type) from None


def has_node_type(node_type: str) -> bool:
    return node_type in _REGISTRY


def all_executors() -> list[AnyExecutor]:
    """Every registered executor, grouped by category then name."""
    order = list(NodeCategory)
    return sorted(_REGISTRY.values(), key=lambda e: (order.index(e.category), e.name))


def trigger_types() -> set[str]:
    return {executor.node_type for executor in _REGISTRY.values() if executor.is_trigger}
