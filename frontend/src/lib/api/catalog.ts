import { api } from "@/lib/api";
import type { NodeType, Overview, WorkflowSummary, WorkflowTemplate } from "@/lib/types";

export const catalogApi = {
  nodeTypes: () => api.get<NodeType[]>("/api/node-types"),
  templates: () => api.get<WorkflowTemplate[]>("/api/templates"),
  createFromTemplate: (templateId: string, name?: string) =>
    api.post<WorkflowSummary>(`/api/templates/${templateId}/create`, { name: name ?? null }),
  overview: () => api.get<Overview>("/api/overview"),
};
