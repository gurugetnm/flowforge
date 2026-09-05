"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Copy, MoreHorizontal, PenLine, Power, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/status-badge";
import { relativeTime } from "@/lib/format";
import { pluralize } from "@/lib/format";
import type { WorkflowSummary } from "@/lib/types";

interface Props {
  workflow: WorkflowSummary;
  onRename: (workflow: WorkflowSummary) => void;
  onDuplicate: (workflow: WorkflowSummary) => void;
  onDelete: (workflow: WorkflowSummary) => void;
  onToggleStatus: (workflow: WorkflowSummary) => void;
  busy?: boolean;
}

export function WorkflowCard({
  workflow,
  onRename,
  onDuplicate,
  onDelete,
  onToggleStatus,
  busy = false,
}: Props) {
  return (
    <li className="group border-border-base hover:bg-surface relative flex items-start justify-between gap-3 border-b px-4 py-3 last:border-b-0">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <Link
            href={`/workflows/${workflow.id}`}
            className="text-text hover:text-accent truncate text-sm font-medium"
          >
            {workflow.name}
          </Link>
          <StatusBadge status={workflow.status} />
        </div>
        {workflow.description && (
          <p className="text-text-muted mt-1 line-clamp-2 text-sm">{workflow.description}</p>
        )}
        <p className="text-text-subtle mt-1.5 text-xs">
          {pluralize(workflow.node_count, "node")} · edited {relativeTime(workflow.updated_at)}
        </p>
      </div>

      <WorkflowMenu
        workflow={workflow}
        busy={busy}
        onRename={onRename}
        onDuplicate={onDuplicate}
        onDelete={onDelete}
        onToggleStatus={onToggleStatus}
      />
    </li>
  );
}

function WorkflowMenu({ workflow, busy, onRename, onDuplicate, onDelete, onToggleStatus }: Props) {
  const [open, setOpen] = useState(false);
  const container = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    function handlePointerDown(event: MouseEvent) {
      if (!container.current?.contains(event.target as Node)) setOpen(false);
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  const activating = workflow.status !== "active";

  const items = [
    { label: "Rename", icon: PenLine, run: () => onRename(workflow) },
    {
      label: activating ? "Activate" : "Move to draft",
      icon: Power,
      run: () => onToggleStatus(workflow),
    },
    { label: "Duplicate", icon: Copy, run: () => onDuplicate(workflow) },
    { label: "Delete", icon: Trash2, run: () => onDelete(workflow), destructive: true },
  ];

  return (
    <div ref={container} className="relative shrink-0">
      <Button
        variant="ghost"
        size="icon"
        loading={busy}
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-haspopup="menu"
        aria-label={`Actions for ${workflow.name}`}
      >
        {!busy && <MoreHorizontal aria-hidden className="h-4 w-4" />}
      </Button>

      {open && (
        <div
          role="menu"
          className="border-border-base bg-surface-raised absolute top-9 right-0 z-20 w-44 overflow-hidden rounded-md border py-1 shadow-lg"
        >
          {items.map(({ label, icon: Icon, run, destructive }) => (
            <button
              key={label}
              type="button"
              role="menuitem"
              onClick={() => {
                setOpen(false);
                run();
              }}
              className={`hover:bg-surface flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm transition-colors ${
                destructive ? "text-danger" : "text-text"
              }`}
            >
              <Icon aria-hidden className="h-3.5 w-3.5" />
              {label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
