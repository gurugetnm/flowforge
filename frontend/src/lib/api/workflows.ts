import { api } from "@/lib/api";
import type {
  Page,
  ValidationResult,
  WorkflowDetail,
  WorkflowGraph,
  WorkflowStatus,
  WorkflowSummary,
} from "@/lib/types";

export interface WorkflowFilters {
  search?: string;
  status?: WorkflowStatus | "";
  limit?: number;
  offset?: number;
}

export const workflowsApi = {
  list: (filters: WorkflowFilters = {}) =>
    api.get<Page<WorkflowSummary>>("/api/workflows", { query: { ...filters } }),
  get: (id: string) => api.get<WorkflowDetail>(`/api/workflows/${id}`),
  create: (body: { name: string; description?: string }) =>
    api.post<WorkflowSummary>("/api/workflows", body),
  update: (id: string, body: { name?: string; description?: string; status?: WorkflowStatus }) =>
    api.patch<WorkflowSummary>(`/api/workflows/${id}`, body),
  remove: (id: string) => api.delete<void>(`/api/workflows/${id}`),
  duplicate: (id: string) => api.post<WorkflowSummary>(`/api/workflows/${id}/duplicate`),
  graph: (id: string) => api.get<WorkflowGraph>(`/api/workflows/${id}/graph`),
  saveGraph: (id: string, graph: WorkflowGraph) =>
    api.put<WorkflowGraph>(`/api/workflows/${id}/graph`, graph),
  validate: (id: string) => api.get<ValidationResult>(`/api/workflows/${id}/validate`),
};
