import { describe, expect, it } from "vitest";

import {
  graphFingerprint,
  outputsFor,
  toApiGraph,
  toFlowEdges,
  toFlowNodes,
  type FlowNode,
} from "@/components/editor/graph-model";
import type { NodeType, WorkflowGraph } from "@/lib/types";

const logType: NodeType = {
  type: "log",
  name: "Log",
  category: "action",
  description: "Writes a message.",
  accepts_input: true,
  is_trigger: false,
  outputs: [{ key: "out", label: "Output", description: "" }],
  fields: [],
  default_configuration: { message: "", level: "info" },
};

const switchType: NodeType = {
  ...logType,
  type: "switch",
  name: "Switch",
  category: "logic",
  outputs: [{ key: "default", label: "Default", description: "" }],
};

const catalog = new Map([
  [logType.type, logType],
  [switchType.type, switchType],
]);

const graph: WorkflowGraph = {
  nodes: [
    {
      id: "11111111-1111-4111-8111-111111111111",
      type: "log",
      label: "Write log",
      configuration: { message: "hi" },
      position: { x: 10.4, y: 20.6 },
    },
    {
      id: "22222222-2222-4222-8222-222222222222",
      type: "log",
      label: "Second",
      configuration: {},
      position: { x: 200, y: 0 },
    },
  ],
  edges: [
    {
      id: "33333333-3333-4333-8333-333333333333",
      source: "11111111-1111-4111-8111-111111111111",
      target: "22222222-2222-4222-8222-222222222222",
      source_handle: "out",
      target_handle: "in",
    },
  ],
};

describe("graph translation", () => {
  it("round trips through the React Flow shape", () => {
    const nodes = toFlowNodes(graph, catalog);
    const edges = toFlowEdges(graph);

    const result = toApiGraph(nodes, edges);

    expect(result.nodes.map((node) => node.id)).toEqual(graph.nodes.map((node) => node.id));
    expect(result.nodes[0].label).toBe("Write log");
    expect(result.nodes[0].configuration).toEqual({ message: "hi" });
    expect(result.edges[0]).toEqual(graph.edges[0]);
  });

  it("rounds positions so the stored graph stays tidy", () => {
    const result = toApiGraph(toFlowNodes(graph, catalog), []);

    expect(result.nodes[0].position).toEqual({ x: 10, y: 21 });
  });

  it("attaches the node definition from the catalog", () => {
    const [node] = toFlowNodes(graph, catalog);

    expect(node.data.definition?.name).toBe("Log");
  });

  it("leaves the definition undefined for a type the server does not have", () => {
    const [node] = toFlowNodes(
      { ...graph, nodes: [{ ...graph.nodes[0], type: "quantum_flux" }] },
      catalog,
    );

    expect(node.data.definition).toBeUndefined();
  });

  it("marks nodes reported as invalid", () => {
    const [node] = toFlowNodes(graph, catalog, new Set([graph.nodes[0].id]));

    expect(node.data.hasError).toBe(true);
  });
});

describe("graphFingerprint", () => {
  it("is stable across node and edge ordering", () => {
    const reversed: WorkflowGraph = { nodes: [...graph.nodes].reverse(), edges: graph.edges };

    expect(graphFingerprint(reversed)).toBe(graphFingerprint(graph));
  });

  it("ignores sub-pixel movement", () => {
    const nudged: WorkflowGraph = {
      ...graph,
      nodes: [{ ...graph.nodes[0], position: { x: 10.2, y: 20.9 } }, graph.nodes[1]],
    };

    expect(graphFingerprint(nudged)).toBe(graphFingerprint(graph));
  });

  it("changes when a node is moved a real distance", () => {
    const moved: WorkflowGraph = {
      ...graph,
      nodes: [{ ...graph.nodes[0], position: { x: 90, y: 20 } }, graph.nodes[1]],
    };

    expect(graphFingerprint(moved)).not.toBe(graphFingerprint(graph));
  });

  it("changes when configuration is edited", () => {
    const edited: WorkflowGraph = {
      ...graph,
      nodes: [{ ...graph.nodes[0], configuration: { message: "changed" } }, graph.nodes[1]],
    };

    expect(graphFingerprint(edited)).not.toBe(graphFingerprint(graph));
  });

  it("changes when an edge is removed", () => {
    expect(graphFingerprint({ ...graph, edges: [] })).not.toBe(graphFingerprint(graph));
  });
});

describe("outputsFor", () => {
  const base: FlowNode["data"] = {
    label: "Route",
    nodeType: "switch",
    configuration: {},
    definition: switchType,
  };

  it("gives a switch one handle per case plus a default", () => {
    const outputs = outputsFor({ ...base, configuration: { cases: ["opened", "closed"] } });

    expect(outputs).toEqual([
      { key: "case:0", label: "opened" },
      { key: "case:1", label: "closed" },
      { key: "default", label: "Default" },
    ]);
  });

  it("skips blank cases", () => {
    const outputs = outputsFor({ ...base, configuration: { cases: ["opened", "  "] } });

    expect(outputs.map((output) => output.key)).toEqual(["case:0", "default"]);
  });

  it("uses the declared outputs for every other node type", () => {
    const outputs = outputsFor({ ...base, nodeType: "log", definition: logType });

    expect(outputs).toEqual([{ key: "out", label: "Output" }]);
  });

  it("falls back to a single output when the type is unknown", () => {
    const outputs = outputsFor({ ...base, nodeType: "quantum_flux", definition: undefined });

    expect(outputs).toEqual([{ key: "out", label: "Output" }]);
  });
});
