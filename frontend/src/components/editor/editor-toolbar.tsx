"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Check, Copy, Play, Save, Webhook } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { StatusBadge } from "@/components/ui/status-badge";
import { useToast } from "@/components/ui/toast";
import { API_BASE_URL } from "@/lib/api";
import { workflowsApi } from "@/lib/api/workflows";
import { queryKeys } from "@/lib/queries";
import type { ValidationResult, WorkflowDetail } from "@/lib/types";

interface Props {
  workflow: WorkflowDetail;
  /** Only workflows with a webhook trigger can be called at their endpoint. */
  hasWebhookTrigger: boolean;
  isDirty: boolean;
  saving: boolean;
  running: boolean;
  validation: ValidationResult | undefined;
  onSave: () => void;
  onRun: () => void;
}

export function EditorToolbar({
  workflow,
  hasWebhookTrigger,
  isDirty,
  saving,
  running,
  validation,
  onSave,
  onRun,
}: Props) {
  const queryClient = useQueryClient();
  const { notify } = useToast();
  const [webhookOpen, setWebhookOpen] = useState(false);

  const toggleStatus = useMutation({
    mutationFn: () =>
      workflowsApi.update(workflow.id, {
        status: workflow.status === "active" ? "draft" : "active",
      }),
    onSuccess: async (updated) => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.workflow(workflow.id) });
      await queryClient.invalidateQueries({ queryKey: queryKeys.workflows() });
      notify(
        updated.status === "active" ? "Workflow activated." : "Workflow moved back to draft.",
        "success",
      );
    },
    onError: () => notify("Could not change the status.", "error"),
  });

  const errorCount = validation?.errors.length ?? 0;

  return (
    <header className="border-border-base bg-bg flex flex-wrap items-center gap-2 border-b px-3 py-2">
      <Link
        href="/workflows"
        aria-label="Back to workflows"
        className="text-text-muted hover:bg-surface hover:text-text rounded p-1.5 transition-colors"
      >
        <ArrowLeft aria-hidden className="h-4 w-4" />
      </Link>

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <h1 className="text-text truncate text-sm font-semibold">{workflow.name}</h1>
          <StatusBadge status={workflow.status} />
        </div>
        <p className="text-text-subtle text-xs">
          {isDirty ? "Unsaved changes" : saving ? "Saving…" : "All changes saved"}
          {errorCount > 0 && ` · ${errorCount} problem${errorCount === 1 ? "" : "s"}`}
        </p>
      </div>

      <div className="flex items-center gap-1.5">
        {hasWebhookTrigger && (
          <Button size="sm" onClick={() => setWebhookOpen(true)}>
            <Webhook aria-hidden className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Webhook</span>
          </Button>
        )}
        <Button size="sm" loading={toggleStatus.isPending} onClick={() => toggleStatus.mutate()}>
          {workflow.status === "active" ? "Deactivate" : "Activate"}
        </Button>
        <Button size="sm" onClick={onSave} loading={saving} disabled={!isDirty && !saving}>
          <Save aria-hidden className="h-3.5 w-3.5" />
          Save
        </Button>
        <Button
          size="sm"
          variant="primary"
          onClick={onRun}
          loading={running}
          title={isDirty ? "Save your changes before running" : "Run this workflow"}
        >
          <Play aria-hidden className="h-3.5 w-3.5" />
          Run
        </Button>
      </div>

      <WebhookDialog
        open={webhookOpen}
        onClose={() => setWebhookOpen(false)}
        url={`${API_BASE_URL}${workflow.webhook_path}`}
        isActive={workflow.status === "active"}
      />
    </header>
  );
}

function WebhookDialog({
  open,
  onClose,
  url,
  isActive,
}: {
  open: boolean;
  onClose: () => void;
  url: string;
  isActive: boolean;
}) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      // The URL stays selectable if the clipboard is unavailable.
    }
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Webhook endpoint"
      description="Send a request here to run this workflow. Treat the URL as a secret: anyone who has it can trigger the workflow."
    >
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <code className="border-border-base bg-surface text-text min-w-0 flex-1 scrollbar-thin overflow-x-auto rounded border px-2.5 py-2 font-mono text-xs whitespace-nowrap">
            {url}
          </code>
          <Button size="sm" onClick={() => void copy()}>
            {copied ? (
              <Check aria-hidden className="h-3.5 w-3.5" />
            ) : (
              <Copy aria-hidden className="h-3.5 w-3.5" />
            )}
            {copied ? "Copied" : "Copy"}
          </Button>
        </div>

        {!isActive && (
          <p className="border-warning/30 bg-warning-soft text-warning rounded border px-2.5 py-2 text-xs">
            This workflow is a draft, so the endpoint will reject calls. Activate it first.
          </p>
        )}

        <p className="text-text-muted text-xs">
          The request body, query string and a small set of headers are passed to the trigger as{" "}
          <code className="font-mono">{"{{ trigger.body }}"}</code>,{" "}
          <code className="font-mono">{"{{ trigger.query }}"}</code> and{" "}
          <code className="font-mono">{"{{ trigger.headers }}"}</code>.
        </p>
      </div>
    </Dialog>
  );
}
