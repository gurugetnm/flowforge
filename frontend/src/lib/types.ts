/** Types mirroring the FlowForge API responses. */

export type WorkflowStatus = "draft" | "active" | "archived";
export type ExecutionStatus = "pending" | "running" | "succeeded" | "failed";
export type NodeRunStatus = "pending" | "running" | "succeeded" | "failed" | "skipped";
export type ExecutionTrigger = "manual" | "webhook" | "retry";
export type NodeCategory = "trigger" | "action" | "logic" | "data";

export type ControlType =
  "text" | "textarea" | "number" | "boolean" | "select" | "json" | "key_value" | "code";

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface User {
  id: string;
  email: string;
  name: string;
  created_at: string;
}

export interface WorkflowSummary {
  id: string;
  name: string;
  description: string;
  status: WorkflowStatus;
  node_count: number;
  created_at: string;
  updated_at: string;
}

export interface WorkflowDetail extends WorkflowSummary {
  webhook_path: string;
  webhook_token: string;
}

export interface NodePosition {
  x: number;
  y: number;
}

export interface GraphNode {
  id: string;
  type: string;
  label: string;
  configuration: Record<string, unknown>;
  position: NodePosition;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  source_handle: string;
  target_handle: string;
}

export interface WorkflowGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface FieldOption {
  value: string;
  label: string;
}

export interface NodeField {
  key: string;
  label: string;
  control: ControlType;
  required: boolean;
  default: unknown;
  help_text: string;
  placeholder: string;
  options: FieldOption[];
  supports_expressions: boolean;
  depends_on: string | null;
  depends_on_values: string[];
}

export interface NodeOutput {
  key: string;
  label: string;
  description: string;
}

export interface NodeType {
  type: string;
  name: string;
  category: NodeCategory;
  description: string;
  accepts_input: boolean;
  is_trigger: boolean;
  outputs: NodeOutput[];
  fields: NodeField[];
  default_configuration: Record<string, unknown>;
}

export interface ValidationIssue {
  code: string;
  severity: "error" | "warning";
  message: string;
  node_id: string | null;
  node_label: string | null;
  field: string | null;
}

export interface ValidationResult {
  is_valid: boolean;
  errors: ValidationIssue[];
  warnings: ValidationIssue[];
}

export interface ExecutionNodeRun {
  id: string;
  node_id: string | null;
  node_type: string;
  node_label: string;
  status: NodeRunStatus;
  sequence: number;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  logs: { messages?: string[] };
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
}

export interface ExecutionSummary {
  id: string;
  workflow_id: string;
  workflow_name: string;
  status: ExecutionStatus;
  trigger: ExecutionTrigger;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  retry_of_id: string | null;
  created_at: string;
}

export interface ExecutionDetail extends ExecutionSummary {
  trigger_payload: Record<string, unknown>;
  variables: Record<string, unknown>;
  node_runs: ExecutionNodeRun[];
}

export interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  node_count: number;
  node_types: string[];
}

export interface Overview {
  workflow_count: number;
  active_workflow_count: number;
  execution_counts: Record<ExecutionStatus, number>;
  recent_executions: ExecutionSummary[];
}
