"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import {
  AlertCircle,
  ArrowRightLeft,
  Braces,
  CheckCircle2,
  Clock,
  Database,
  FileText,
  Globe,
  GitBranch,
  MinusCircle,
  Play,
  Split,
  Webhook,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { outputsFor, type FlowNode as FlowNodeType } from "@/components/editor/graph-model";
import { cn } from "@/lib/cn";
import type { NodeCategory } from "@/lib/types";

const NODE_ICONS: Record<string, LucideIcon> = {
  manual_trigger: Play,
  webhook_trigger: Webhook,
  http_request: Globe,
  json_transform: ArrowRightLeft,
  delay: Clock,
  log: FileText,
  condition: GitBranch,
  switch: Split,
  set_variable: Database,
  json_input: Braces,
};

const CATEGORY_ACCENTS: Record<NodeCategory, string> = {
  trigger: "border-l-success",
  action: "border-l-accent",
  logic: "border-l-warning",
  data: "border-l-info",
};

const RUN_STATUS_RING: Record<string, string> = {
  succeeded: "ring-2 ring-success",
  failed: "ring-2 ring-danger",
  running: "ring-2 ring-info",
  skipped: "opacity-50",
};

/** The card rendered for every node on the canvas. */
export const WorkflowFlowNode = memo(function WorkflowFlowNode({
  data,
  selected,
}: NodeProps<FlowNodeType>) {
  const definition = data.definition;
  const Icon = NODE_ICONS[data.nodeType] ?? Braces;
  const outputs = outputsFor(data);
  const acceptsInput = definition?.accepts_input ?? true;
  const isBranching = outputs.length > 1;

  return (
    <div
      className={cn(
        "border-border-base bg-surface-raised w-52 rounded-md border border-l-4 shadow-sm transition-shadow",
        definition ? CATEGORY_ACCENTS[definition.category] : "border-l-danger",
        selected && "border-accent shadow-md",
        data.hasError && "border-danger",
        data.runStatus && RUN_STATUS_RING[data.runStatus],
      )}
    >
      {acceptsInput && (
        <Handle
          type="target"
          position={Position.Left}
          id="in"
          className="!border-bg !bg-border-strong !h-2.5 !w-2.5 !border-2"
        />
      )}

      <div className="flex items-start gap-2 px-2.5 py-2">
        <Icon aria-hidden className="text-text-muted mt-0.5 h-4 w-4 shrink-0" />
        <div className="min-w-0 flex-1">
          <p className="text-text truncate text-xs font-medium" title={data.label}>
            {data.label}
          </p>
          <p className="text-text-subtle truncate font-mono text-[11px]">
            {definition?.name ?? `Unknown: ${data.nodeType}`}
          </p>
        </div>
        <NodeStatusIcon status={data.runStatus} hasError={data.hasError} />
      </div>

      {isBranching ? (
        <ul className="border-border-base border-t">
          {outputs.map((output, index) => (
            <li
              key={output.key}
              className="border-border-base text-text-muted relative flex justify-end border-b px-2.5 py-1 text-[11px] last:border-b-0"
            >
              <span className="max-w-[8rem] truncate">{output.label}</span>
              <Handle
                type="source"
                position={Position.Right}
                id={output.key}
                style={{ top: "50%" }}
                className="!border-bg !bg-border-strong !h-2.5 !w-2.5 !border-2"
                data-testid={`handle-${output.key}-${index}`}
              />
            </li>
          ))}
        </ul>
      ) : (
        <Handle
          type="source"
          position={Position.Right}
          id={outputs[0]?.key ?? "out"}
          className="!border-bg !bg-border-strong !h-2.5 !w-2.5 !border-2"
        />
      )}
    </div>
  );
});

function NodeStatusIcon({ status, hasError }: { status?: string; hasError?: boolean }) {
  if (hasError && !status) {
    return (
      <AlertCircle
        aria-label="This node has a configuration problem"
        className="text-danger h-3.5 w-3.5"
      />
    );
  }
  if (status === "succeeded") {
    return <CheckCircle2 aria-label="Completed" className="text-success h-3.5 w-3.5" />;
  }
  if (status === "failed") {
    return <AlertCircle aria-label="Failed" className="text-danger h-3.5 w-3.5" />;
  }
  if (status === "skipped") {
    return <MinusCircle aria-label="Skipped" className="text-text-subtle h-3.5 w-3.5" />;
  }
  return null;
}
