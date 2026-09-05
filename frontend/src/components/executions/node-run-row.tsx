"use client";

import { useState } from "react";
import { AlertCircle, CheckCircle2, ChevronRight, Circle, MinusCircle } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { JsonView } from "@/components/executions/json-view";
import { cn } from "@/lib/cn";
import { duration } from "@/lib/format";
import type { ExecutionNodeRun, NodeRunStatus } from "@/lib/types";

const STATUS_ICONS: Record<NodeRunStatus, LucideIcon> = {
  succeeded: CheckCircle2,
  failed: AlertCircle,
  running: Circle,
  pending: Circle,
  skipped: MinusCircle,
};

const STATUS_COLORS: Record<NodeRunStatus, string> = {
  succeeded: "text-success",
  failed: "text-danger",
  running: "text-info",
  pending: "text-text-subtle",
  skipped: "text-text-subtle",
};

const STATUS_LABELS: Record<NodeRunStatus, string> = {
  succeeded: "completed",
  failed: "failed",
  running: "running",
  pending: "pending",
  skipped: "skipped",
};

/** One node inside a run: status, timing, and its data when expanded. */
export function NodeRunRow({ run }: { run: ExecutionNodeRun }) {
  // Failed nodes open by default, because that is what the reader came for.
  const [open, setOpen] = useState(run.status === "failed");

  const Icon = STATUS_ICONS[run.status];
  const messages = run.logs.messages ?? [];
  const inspectable = run.status !== "skipped";

  return (
    <li className="border-border-base border-b last:border-b-0">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        disabled={!inspectable}
        className={cn(
          "flex w-full items-center gap-3 px-4 py-2.5 text-left transition-colors",
          inspectable ? "hover:bg-surface" : "cursor-default opacity-70",
        )}
      >
        <ChevronRight
          aria-hidden
          className={cn(
            "text-text-subtle h-3.5 w-3.5 shrink-0 transition-transform",
            open && "rotate-90",
            !inspectable && "invisible",
          )}
        />
        <Icon aria-hidden className={cn("h-4 w-4 shrink-0", STATUS_COLORS[run.status])} />
        <div className="min-w-0 flex-1">
          <p className="text-text truncate text-sm font-medium">{run.node_label}</p>
          <p className="text-text-subtle font-mono text-xs">{run.node_type}</p>
        </div>
        <span className={cn("shrink-0 text-xs", STATUS_COLORS[run.status])}>
          {STATUS_LABELS[run.status]}
        </span>
        <span className="text-text-muted w-16 shrink-0 text-right font-mono text-xs tabular-nums">
          {duration(run.duration_ms)}
        </span>
      </button>

      {open && inspectable && (
        <div className="border-border-base bg-surface/50 space-y-3 border-t px-4 py-3">
          {run.error && (
            <div role="alert" className="border-danger/30 bg-danger-soft rounded border p-2.5">
              <p className="text-danger text-xs font-medium tracking-wide uppercase">Error</p>
              <p className="text-text mt-1 font-mono text-xs break-words">{run.error}</p>
            </div>
          )}

          {messages.length > 0 && (
            <div>
              <h4 className="text-text-subtle text-xs font-medium tracking-wide uppercase">Log</h4>
              <ul className="border-border-base bg-surface text-text mt-1 space-y-0.5 rounded border p-2.5 font-mono text-xs">
                {messages.map((message, index) => (
                  <li key={index}>{message}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="grid gap-3 lg:grid-cols-2">
            <JsonView label="Input" value={run.input} emptyText="No input" />
            <JsonView
              label="Output"
              value={run.output}
              emptyText={run.status === "failed" ? "The node produced no output" : "No output"}
            />
          </div>
        </div>
      )}
    </li>
  );
}
