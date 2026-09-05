import { api } from "@/lib/api";
import type { ExecutionDetail, ExecutionStatus, ExecutionSummary, Page } from "@/lib/types";

export interface ExecutionFilters {
  workflow_id?: string;
  status?: ExecutionStatus | "";
  limit?: number;
  offset?: number;
}

export const executionsApi = {
  list: (filters: ExecutionFilters = {}) =>
    api.get<Page<ExecutionSummary>>("/api/executions", { query: { ...filters } }),
  get: (id: string) => api.get<ExecutionDetail>(`/api/executions/${id}`),
  run: (workflowId: string, payload: Record<string, unknown> = {}) =>
    api.post<ExecutionDetail>(`/api/workflows/${workflowId}/run`, { payload }),
  retry: (id: string) => api.post<ExecutionDetail>(`/api/executions/${id}/retry`),
};
