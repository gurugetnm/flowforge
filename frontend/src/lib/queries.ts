/** Query keys, kept in one place so invalidation stays consistent. */

export const queryKeys = {
  session: ["session"] as const,
  overview: ["overview"] as const,
  nodeTypes: ["node-types"] as const,
  templates: ["templates"] as const,
  workflows: (filters?: Record<string, unknown>) =>
    filters ? (["workflows", filters] as const) : (["workflows"] as const),
  workflow: (id: string) => ["workflow", id] as const,
  workflowGraph: (id: string) => ["workflow", id, "graph"] as const,
  workflowValidation: (id: string) => ["workflow", id, "validation"] as const,
  executions: (filters?: Record<string, unknown>) =>
    filters ? (["executions", filters] as const) : (["executions"] as const),
  execution: (id: string) => ["execution", id] as const,
};
