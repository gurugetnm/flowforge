/**
 * Translation between the API's graph shape and the one React Flow works with.
 *
 * The API is the source of truth for ids, so a node keeps the same id from the
 * moment it is dropped on the canvas through every save, which is what lets
 * execution history keep pointing at it.
 */

import type { Edge, Node } from "@xyflow/react";

import type { GraphNode, NodeType, WorkflowGraph } from "@/lib/types";

export interface FlowNodeData extends Record<string, unknown> {
  label: string;
  nodeType: string;
  configuration: Record<string, unknown>;
  /** Filled in from the node catalog; absent if the type is not installed. */
  definition: NodeType | undefined;
  /** Set while inspecting a run, to colour the node by its outcome. */
  runStatus?: "succeeded" | "failed" | "skipped" | "running";
  hasError?: boolean;
}

export type FlowNode = Node<FlowNodeData, "workflowNode">;
export type FlowEdge = Edge;

export function toFlowNodes(
  graph: WorkflowGraph,
  catalog: Map<string, NodeType>,
  invalidNodeIds: Set<string> = new Set(),
): FlowNode[] {
  return graph.nodes.map((node) => ({
    id: node.id,
    type: "workflowNode" as const,
    position: node.position,
    data: {
      label: node.label,
      nodeType: node.type,
      configuration: node.configuration,
      definition: catalog.get(node.type),
      hasError: invalidNodeIds.has(node.id),
    },
  }));
}

export function toFlowEdges(graph: WorkflowGraph): FlowEdge[] {
  return graph.edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    sourceHandle: edge.source_handle,
    targetHandle: edge.target_handle,
  }));
}

export function toApiGraph(nodes: FlowNode[], edges: FlowEdge[]): WorkflowGraph {
  return {
    nodes: nodes.map((node): GraphNode => ({
      id: node.id,
      type: node.data.nodeType,
      label: node.data.label,
      configuration: node.data.configuration,
      position: { x: Math.round(node.position.x), y: Math.round(node.position.y) },
    })),
    edges: edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      source_handle: edge.sourceHandle ?? "out",
      target_handle: edge.targetHandle ?? "in",
    })),
  };
}

/**
 * A stable string for change detection.
 *
 * Positions are rounded so a sub-pixel drag does not mark the workflow dirty,
 * and both lists are sorted so reordering alone is not a change either.
 */
export function graphFingerprint(graph: WorkflowGraph): string {
  const nodes = [...graph.nodes]
    .sort((a, b) => a.id.localeCompare(b.id))
    .map((node) => ({
      i: node.id,
      t: node.type,
      l: node.label,
      c: node.configuration,
      x: Math.round(node.position.x),
      y: Math.round(node.position.y),
    }));

  const edges = [...graph.edges]
    .sort((a, b) => a.id.localeCompare(b.id))
    .map((edge) => [edge.source, edge.target, edge.source_handle, edge.target_handle]);

  return JSON.stringify({ nodes, edges });
}

/** The outputs a node exposes, which for a Switch depend on its cases. */
export function outputsFor(data: FlowNodeData): { key: string; label: string }[] {
  if (data.nodeType === "switch") {
    const cases = Array.isArray(data.configuration.cases)
      ? (data.configuration.cases as unknown[])
      : [];
    return [
      ...cases
        .map((value, index) => ({ key: `case:${index}`, label: String(value) }))
        .filter((output) => output.label.trim() !== ""),
      { key: "default", label: "Default" },
    ];
  }
  return (
    data.definition?.outputs.map(({ key, label }) => ({ key, label })) ?? [
      { key: "out", label: "Output" },
    ]
  );
}
