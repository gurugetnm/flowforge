import { cn } from "@/lib/cn";
import type { ExecutionStatus, NodeRunStatus, WorkflowStatus } from "@/lib/types";

type AnyStatus = WorkflowStatus | ExecutionStatus | NodeRunStatus;

const STYLES: Record<AnyStatus, string> = {
  draft: "bg-surface text-text-muted border-border-base",
  active: "bg-success-soft text-success border-success/30",
  archived: "bg-surface text-text-subtle border-border-base",
  pending: "bg-surface text-text-muted border-border-base",
  running: "bg-info-soft text-info border-info/30",
  succeeded: "bg-success-soft text-success border-success/30",
  failed: "bg-danger-soft text-danger border-danger/30",
  skipped: "bg-surface text-text-subtle border-border-base",
};

const LABELS: Partial<Record<AnyStatus, string>> = {
  succeeded: "Succeeded",
  failed: "Failed",
  running: "Running",
  pending: "Pending",
  skipped: "Skipped",
  draft: "Draft",
  active: "Active",
  archived: "Archived",
};

export function StatusBadge({ status, className }: { status: AnyStatus; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded border px-1.5 py-0.5 text-xs font-medium",
        STYLES[status],
        className,
      )}
    >
      {LABELS[status] ?? status}
    </span>
  );
}
