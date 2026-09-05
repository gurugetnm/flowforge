"""Reading and replacing the node graph of a workflow."""

import uuid

from sqlalchemy.orm import Session

from app.models import Workflow, WorkflowEdge, WorkflowNode
from app.schemas.graph import (
    GraphEdgeResponse,
    GraphNodeResponse,
    GraphUpdate,
    Position,
    WorkflowGraph,
)


def read_graph(workflow: Workflow) -> WorkflowGraph:
    return WorkflowGraph(
        nodes=[
            GraphNodeResponse(
                id=node.id,
                type=node.node_type,
                label=node.label,
                configuration=node.configuration,
                position=Position(x=node.position_x, y=node.position_y),
            )
            for node in workflow.nodes
        ],
        edges=[
            GraphEdgeResponse(
                id=edge.id,
                source=edge.source_node_id,
                target=edge.target_node_id,
                source_handle=edge.source_handle,
                target_handle=edge.target_handle,
            )
            for edge in workflow.edges
        ],
    )


def replace_graph(session: Session, workflow: Workflow, update: GraphUpdate) -> WorkflowGraph:
    """Persist ``update`` as the workflow's graph.

    Nodes that already exist are updated in place rather than recreated, so
    the `execution_nodes` rows recorded by earlier runs keep pointing at them.
    Edges carry no history and are simply rewritten.
    """
    existing_nodes = {node.id: node for node in workflow.nodes}
    submitted_ids = {node.id for node in update.nodes}

    for node_id, node in existing_nodes.items():
        if node_id not in submitted_ids:
            session.delete(node)

    for incoming in update.nodes:
        existing = existing_nodes.get(incoming.id)
        if existing is None:
            node = WorkflowNode(id=incoming.id, workflow_id=workflow.id)
            session.add(node)
        else:
            node = existing
        node.node_type = incoming.type
        node.label = incoming.label
        node.configuration = incoming.configuration
        node.position_x = incoming.position.x
        node.position_y = incoming.position.y

    # Deleting the edges first keeps the unique connection constraint happy
    # when an edge is re-pointed within a single save.
    for edge in list(workflow.edges):
        session.delete(edge)
    session.flush()

    for incoming_edge in update.edges:
        session.add(
            WorkflowEdge(
                id=incoming_edge.id,
                workflow_id=workflow.id,
                source_node_id=incoming_edge.source,
                target_node_id=incoming_edge.target,
                source_handle=incoming_edge.source_handle,
                target_handle=incoming_edge.target_handle,
            )
        )

    session.flush()
    session.refresh(workflow)
    return read_graph(workflow)


def node_map(workflow: Workflow) -> dict[uuid.UUID, WorkflowNode]:
    return {node.id: node for node in workflow.nodes}
