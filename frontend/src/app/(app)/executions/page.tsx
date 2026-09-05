"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ListChecks } from "lucide-react";

import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Select } from "@/components/ui/field";
import { SkeletonRows } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/ui/status-badge";
import { executionsApi } from "@/lib/api/executions";
import { absoluteTime, duration, pluralize, relativeTime } from "@/lib/format";
import { queryKeys } from "@/lib/queries";
import type { ExecutionStatus } from "@/lib/types";

const PAGE_SIZE = 20;

const TRIGGER_LABELS: Record<string, string> = {
  manual: "Manual",
  webhook: "Webhook",
  retry: "Retry",
};

export default function ExecutionsPage() {
  const [status, setStatus] = useState<ExecutionStatus | "">("");
  const [page, setPage] = useState(0);

  const filters = { status, limit: PAGE_SIZE, offset: page * PAGE_SIZE };
  const { data, isPending, error, refetch, isFetching } = useQuery({
    queryKey: queryKeys.executions(filters),
    queryFn: () => executionsApi.list(filters),
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <div className="mx-auto max-w-5xl space-y-5 p-4 sm:p-6">
      <PageHeader
        title="Executions"
        description="Every run, with the outcome of each node."
        actions={
          <Select
            value={status}
            onChange={(event) => {
              setStatus(event.target.value as ExecutionStatus | "");
              setPage(0);
            }}
            aria-label="Filter by status"
            className="w-40"
          >
            <option value="">All runs</option>
            <option value="succeeded">Successful</option>
            <option value="failed">Failed</option>
            <option value="running">Running</option>
          </Select>
        }
      />

      {isPending ? (
        <SkeletonRows rows={5} />
      ) : error ? (
        <ErrorState error={error} onRetry={() => void refetch()} />
      ) : data.items.length === 0 ? (
        <EmptyState
          icon={ListChecks}
          title={status ? "No runs with that status" : "No runs yet"}
          description={
            status
              ? "Change the filter to see other runs."
              : "Open a workflow and press Run to record your first execution."
          }
          action={
            status ? (
              <Button onClick={() => setStatus("")}>Show all runs</Button>
            ) : (
              <Link href="/workflows" className="text-accent text-sm font-medium hover:underline">
                Go to workflows
              </Link>
            )
          }
        />
      ) : (
        <>
          <div
            className="border-border-base overflow-x-auto rounded-md border"
            aria-busy={isFetching}
          >
            <table className="w-full min-w-[42rem] border-collapse text-sm">
              <caption className="sr-only">Workflow executions, newest first</caption>
              <thead>
                <tr className="border-border-base bg-surface text-text-muted border-b text-left text-xs">
                  <th scope="col" className="px-4 py-2 font-medium">
                    Workflow
                  </th>
                  <th scope="col" className="px-4 py-2 font-medium">
                    Status
                  </th>
                  <th scope="col" className="px-4 py-2 font-medium">
                    Trigger
                  </th>
                  <th scope="col" className="px-4 py-2 font-medium">
                    Started
                  </th>
                  <th scope="col" className="px-4 py-2 font-medium">
                    Duration
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((execution) => (
                  <tr
                    key={execution.id}
                    className="border-border-base hover:bg-surface border-b last:border-b-0"
                  >
                    <td className="max-w-xs px-4 py-2.5">
                      <Link
                        href={`/executions/${execution.id}`}
                        className="text-text hover:text-accent block truncate font-medium"
                      >
                        {execution.workflow_name || "Deleted workflow"}
                      </Link>
                      {execution.error && (
                        <p className="text-danger mt-0.5 truncate text-xs" title={execution.error}>
                          {execution.error}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-2.5">
                      <StatusBadge status={execution.status} />
                    </td>
                    <td className="text-text-muted px-4 py-2.5">
                      {TRIGGER_LABELS[execution.trigger] ?? execution.trigger}
                    </td>
                    <td
                      className="text-text-muted px-4 py-2.5 whitespace-nowrap"
                      title={absoluteTime(execution.started_at)}
                    >
                      {relativeTime(execution.started_at)}
                    </td>
                    <td className="text-text-muted px-4 py-2.5 font-mono text-xs whitespace-nowrap tabular-nums">
                      {duration(execution.duration_ms)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="text-text-muted flex items-center justify-between text-sm">
            <p>{pluralize(data.total, "run")}</p>
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
    </div>
  );
}
