"use client";

import { AlertTriangle, CheckCircle2, XCircle } from "lucide-react";

import { cn } from "@/lib/cn";
import type { ValidationResult } from "@/lib/types";

interface Props {
  result: ValidationResult | undefined;
  onSelectNode: (nodeId: string) => void;
}

/** Lists what would stop the workflow from running, each linked to its node. */
export function ValidationPanel({ result, onSelectNode }: Props) {
  if (!result) return null;

  const issues = [...result.errors, ...result.warnings];

  if (issues.length === 0) {
    return (
      <p className="text-success flex items-center gap-2 px-3 py-2 text-xs">
        <CheckCircle2 aria-hidden className="h-3.5 w-3.5" />
        This workflow is ready to run.
      </p>
    );
  }

  return (
    <ul className="max-h-40 scrollbar-thin overflow-y-auto">
      {issues.map((issue, index) => {
        const isError = issue.severity === "error";
        const Icon = isError ? XCircle : AlertTriangle;

        return (
          <li key={`${issue.code}-${index}`}>
            <button
              type="button"
              disabled={!issue.node_id}
              onClick={() => issue.node_id && onSelectNode(issue.node_id)}
              className={cn(
                "flex w-full items-start gap-2 px-3 py-1.5 text-left text-xs",
                issue.node_id ? "hover:bg-surface" : "cursor-default",
              )}
            >
              <Icon
                aria-hidden
                className={cn(
                  "mt-0.5 h-3.5 w-3.5 shrink-0",
                  isError ? "text-danger" : "text-warning",
                )}
              />
              <span className="text-text">{issue.message}</span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
