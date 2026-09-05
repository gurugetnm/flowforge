"""Graph structure and traversal.

The workflow graph is a directed acyclic graph. This module turns the stored
node and edge rows into an adjacency structure, resolves the order nodes run
in, and reports cycles precisely enough to name the nodes involved.
"""

import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field

from app.models import Workflow, WorkflowEdge, WorkflowNode


@dataclass(frozen=True, slots=True)
class Connection:
    """One directed link, kept alongside the handles it uses."""

    source: uuid.UUID
    target: uuid.UUID
    source_handle: str
    target_handle: str


@dataclass(slots=True)
class WorkflowGraph:
    """An indexed, traversable view of a stored workflow."""

    nodes: dict[uuid.UUID, WorkflowNode]
    connections: list[Connection]
    outgoing: dict[uuid.UUID, list[Connection]] = field(default_factory=lambda: defaultdict(list))
    incoming: dict[uuid.UUID, list[Connection]] = field(default_factory=lambda: defaultdict(list))

    @classmethod
    def from_workflow(cls, workflow: Workflow) -> "WorkflowGraph":
        nodes = {node.id: node for node in workflow.nodes}
        connections = [_to_connection(edge) for edge in workflow.edges]
        graph = cls(nodes=nodes, connections=connections)

        for connection in connections:
            graph.outgoing[connection.source].append(connection)
            graph.incoming[connection.target].append(connection)

        return graph

    def successors(self, node_id: uuid.UUID, handle: str | None = None) -> list[uuid.UUID]:
        """Nodes reachable from ``node_id``, optionally through one handle."""
        return [
            connection.target
            for connection in self.outgoing[node_id]
            if handle is None or connection.source_handle == handle
        ]

    def used_source_handles(self, node_id: uuid.UUID) -> set[str]:
        return {connection.source_handle for connection in self.outgoing[node_id]}

    def has_incoming(self, node_id: uuid.UUID) -> bool:
        return bool(self.incoming[node_id])

    def reachable_from(self, start: uuid.UUID) -> set[uuid.UUID]:
        """Every node reachable from ``start``, following any handle."""
        seen: set[uuid.UUID] = set()
        queue = deque([start])
        while queue:
            current = queue.popleft()
            if current in seen:
                continue
            seen.add(current)
            queue.extend(self.successors(current))
        return seen

    def topological_order(self) -> list[uuid.UUID]:
        """Return node ids in dependency order.

        Raises `CycleError` when the graph cannot be ordered, naming the nodes
        that take part in the cycle.
        """
        in_degree = {node_id: len(self.incoming[node_id]) for node_id in self.nodes}
        ready = deque(sorted((n for n, d in in_degree.items() if d == 0), key=str))
        order: list[uuid.UUID] = []

        while ready:
            current = ready.popleft()
            order.append(current)
            for connection in self.outgoing[current]:
                in_degree[connection.target] -= 1
                if in_degree[connection.target] == 0:
                    ready.append(connection.target)

        if len(order) != len(self.nodes):
            remaining = [node_id for node_id in self.nodes if node_id not in set(order)]
            raise CycleError(remaining)

        return order

    def label_of(self, node_id: uuid.UUID) -> str:
        node = self.nodes.get(node_id)
        return node.label if node else str(node_id)


class CycleError(ValueError):
    """The graph contains a cycle, so no execution order exists."""

    def __init__(self, node_ids: list[uuid.UUID]) -> None:
        super().__init__("The workflow contains a loop.")
        self.node_ids = node_ids


def _to_connection(edge: WorkflowEdge) -> Connection:
    return Connection(
        source=edge.source_node_id,
        target=edge.target_node_id,
        source_handle=edge.source_handle,
        target_handle=edge.target_handle,
    )
