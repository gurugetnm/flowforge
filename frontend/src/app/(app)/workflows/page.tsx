"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { GitBranch, Plus, Search } from "lucide-react";

import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Input, Select } from "@/components/ui/field";
import { SkeletonRows } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { CreateWorkflowDialog } from "@/components/workflows/create-workflow-dialog";
import { RenameWorkflowDialog } from "@/components/workflows/rename-workflow-dialog";
import { WorkflowCard } from "@/components/workflows/workflow-card";
import { ApiError } from "@/lib/api";
import { workflowsApi } from "@/lib/api/workflows";
import { pluralize } from "@/lib/format";
import { queryKeys } from "@/lib/queries";
import type { WorkflowStatus, WorkflowSummary } from "@/lib/types";
import { useDebounced } from "@/lib/use-debounced";

const PAGE_SIZE = 20;

export default function WorkflowsPage() {
  const queryClient = useQueryClient();
  const { notify } = useToast();

  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<WorkflowStatus | "">("");
  const [page, setPage] = useState(0);
  const [creating, setCreating] = useState(false);
  const [renaming, setRenaming] = useState<WorkflowSummary | null>(null);
  const [deleting, setDeleting] = useState<WorkflowSummary | null>(null);

  const debouncedSearch = useDebounced(search);
  const filters = {
    search: debouncedSearch,
    status,
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
  };

  const { data, isPending, error, refetch, isFetching } = useQuery({
    queryKey: queryKeys.workflows(filters),
    queryFn: () => workflowsApi.list(filters),
  });

  async function refresh() {
    await queryClient.invalidateQueries({ queryKey: queryKeys.workflows() });
  }

  const remove = useMutation({
    mutationFn: (workflow: WorkflowSummary) => workflowsApi.remove(workflow.id),
    onSuccess: async (_, workflow) => {
      await refresh();
      notify(`Deleted "${workflow.name}".`, "success");
      setDeleting(null);
    },
    onError: (apiError) => {
      notify(
        apiError instanceof ApiError ? apiError.message : "Could not delete the workflow.",
        "error",
      );
    },
  });

  const duplicate = useMutation({
    mutationFn: (workflow: WorkflowSummary) => workflowsApi.duplicate(workflow.id),
    onSuccess: async (copy) => {
      await refresh();
      notify(`Created "${copy.name}".`, "success");
    },
    onError: () => notify("Could not duplicate the workflow.", "error"),
  });

  const toggleStatus = useMutation({
    mutationFn: (workflow: WorkflowSummary) =>
      workflowsApi.update(workflow.id, {
        status: workflow.status === "active" ? "draft" : "active",
      }),
    onSuccess: async (updated) => {
      await refresh();
      notify(
        updated.status === "active"
          ? `"${updated.name}" is now active.`
          : `"${updated.name}" moved back to draft.`,
        "success",
      );
    },
    onError: () => notify("Could not change the status.", "error"),
  });

  const busyId = duplicate.variables?.id ?? toggleStatus.variables?.id;
  const hasFilters = debouncedSearch !== "" || status !== "";
  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <div className="mx-auto max-w-4xl space-y-5 p-4 sm:p-6">
      <PageHeader
        title="Workflows"
        description="Build, edit and run your automations."
        actions={
          <Button variant="primary" onClick={() => setCreating(true)}>
            <Plus aria-hidden className="h-4 w-4" />
            New workflow
          </Button>
        }
      />

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-0 flex-1">
          <Search
            aria-hidden
            className="text-text-subtle pointer-events-none absolute top-1/2 left-2.5 h-4 w-4 -translate-y-1/2"
          />
          <Input
            type="search"
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              setPage(0);
            }}
            placeholder="Search workflows"
            aria-label="Search workflows"
            className="pl-8"
          />
        </div>
        <Select
          value={status}
          onChange={(event) => {
            setStatus(event.target.value as WorkflowStatus | "");
            setPage(0);
          }}
          aria-label="Filter by status"
          className="w-36"
        >
          <option value="">All statuses</option>
          <option value="draft">Draft</option>
          <option value="active">Active</option>
          <option value="archived">Archived</option>
        </Select>
      </div>

      {isPending ? (
        <SkeletonRows rows={4} />
      ) : error ? (
        <ErrorState error={error} onRetry={() => void refetch()} />
      ) : data.items.length === 0 ? (
        <EmptyState
          icon={GitBranch}
          title={hasFilters ? "No matching workflows" : "No workflows yet"}
          description={
            hasFilters
              ? "Try a different search term or clear the status filter."
              : "Create your first workflow, or start from one of the templates."
          }
          action={
            hasFilters ? (
              <Button
                onClick={() => {
                  setSearch("");
                  setStatus("");
                }}
              >
                Clear filters
              </Button>
            ) : (
              <Button variant="primary" onClick={() => setCreating(true)}>
                <Plus aria-hidden className="h-4 w-4" />
                New workflow
              </Button>
            )
          }
        />
      ) : (
        <>
          <div
            className="border-border-base overflow-hidden rounded-md border"
            aria-busy={isFetching}
          >
            <ul>
              {data.items.map((workflow) => (
                <WorkflowCard
                  key={workflow.id}
                  workflow={workflow}
                  busy={busyId === workflow.id}
                  onRename={setRenaming}
                  onDelete={setDeleting}
                  onDuplicate={(item) => duplicate.mutate(item)}
                  onToggleStatus={(item) => toggleStatus.mutate(item)}
                />
              ))}
            </ul>
          </div>

          <div className="text-text-muted flex items-center justify-between text-sm">
            <p>{pluralize(data.total, "workflow")}</p>
            {totalPages > 1 && (
              <div className="flex items-center gap-2">
                <Button size="sm" disabled={page === 0} onClick={() => setPage((n) => n - 1)}>
                  Previous
                </Button>
                <span className="tabular-nums">
                  {page + 1} / {totalPages}
                </span>
                <Button
                  size="sm"
                  disabled={page + 1 >= totalPages}
                  onClick={() => setPage((n) => n + 1)}
                >
                  Next
                </Button>
              </div>
            )}
          </div>
        </>
      )}

      <CreateWorkflowDialog open={creating} onClose={() => setCreating(false)} />
      <RenameWorkflowDialog workflow={renaming} onClose={() => setRenaming(null)} />
      <ConfirmDialog
        open={deleting !== null}
        onClose={() => setDeleting(null)}
        onConfirm={() => deleting && remove.mutate(deleting)}
        title="Delete workflow"
        description={`"${deleting?.name}" and its run history will be permanently deleted. This cannot be undone.`}
        confirmLabel="Delete workflow"
        destructive
        loading={remove.isPending}
      />
    </div>
  );
}
