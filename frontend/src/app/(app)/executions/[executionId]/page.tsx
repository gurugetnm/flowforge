"use client";

import { use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, RotateCw } from "lucide-react";

import { JsonView } from "@/components/executions/json-view";
import { NodeRunRow } from "@/components/executions/node-run-row";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { SkeletonRows } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/ui/status-badge";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api";
import { executionsApi } from "@/lib/api/executions";
import { absoluteTime, duration, pluralize } from "@/lib/format";
import { queryKeys } from "@/lib/queries";

export default function ExecutionDetailPage({
  params,
}: {
  params: Promise<{ executionId: string }>;
}) {
  const { executionId } = use(params);
  const router = useRouter();
  const queryClient = useQueryClient();
  const { notify } = useToast();

  const { data, isPending, error, refetch } = useQuery({
    queryKey: queryKeys.execution(executionId),
    queryFn: () => executionsApi.get(executionId),
  });

  const retry = useMutation({
    mutationFn: () => executionsApi.retry(executionId),
    onSuccess: async (execution) => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.executions() });
      notify("Started a new run from this execution.", "success");
      router.push(`/executions/${execution.id}`);
    },
    onError: (retryError) => {
      notify(
        retryError instanceof ApiError ? retryError.message : "Could not retry this run.",
        "error",
      );
    },
  });

  if (isPending) {
    return (
      <div className="mx-auto max-w-4xl p-4 sm:p-6">
        <SkeletonRows rows={4} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-4xl p-4 sm:p-6">
        <ErrorState
          error={error}
          onRetry={() => void refetch()}
          title={error instanceof ApiError && error.isNotFound ? "Run not found" : undefined}
        />
      </div>
    );
  }

  const succeeded = data.node_runs.filter((run) => run.status === "succeeded").length;
  const failed = data.node_runs.filter((run) => run.status === "failed").length;
  const skipped = data.node_runs.filter((run) => run.status === "skipped").length;

  return (
    <div className="mx-auto max-w-4xl space-y-5 p-4 sm:p-6">
      <Link
        href="/executions"
        className="text-text-muted hover:text-text inline-flex items-center gap-1.5 text-sm"
      >
        <ArrowLeft aria-hidden className="h-3.5 w-3.5" />
        All executions
      </Link>

      <PageHeader
        title={data.workflow_name || "Deleted workflow"}
        description={`Run started ${absoluteTime(data.started_at)}`}
        actions={
          <Button variant="primary" loading={retry.isPending} onClick={() => retry.mutate()}>
            <RotateCw aria-hidden className="h-3.5 w-3.5" />
            Retry run
          </Button>
        }
      />

      <dl className="border-border-base bg-surface-raised grid grid-cols-2 gap-3 rounded-md border p-4 sm:grid-cols-4">
        <Detail label="Status">
          <StatusBadge status={data.status} />
        </Detail>
        <Detail label="Duration">
          <span className="text-text font-mono text-sm tabular-nums">
            {duration(data.duration_ms)}
          </span>
        </Detail>
        <Detail label="Trigger">
          <span className="text-text text-sm capitalize">{data.trigger}</span>
        </Detail>
        <Detail label="Execution ID">
          <span className="text-text-muted font-mono text-xs break-all">{data.id}</span>
        </Detail>
      </dl>

      {data.error && (
        <div role="alert" className="border-danger/30 bg-danger-soft rounded-md border p-3">
          <p className="text-danger text-xs font-medium tracking-wide uppercase">Run failed</p>
          <p className="text-text mt-1 font-mono text-sm break-words">{data.error}</p>
        </div>
      )}

      {data.retry_of_id && (
        <p className="text-text-muted text-sm">
          This run is a retry of{" "}
          <Link
            href={`/executions/${data.retry_of_id}`}
            className="text-accent font-mono hover:underline"
          >
            {data.retry_of_id.slice(0, 8)}
          </Link>
          .
        </p>
      )}

      <section aria-labelledby="node-results" className="space-y-2">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 id="node-results" className="text-text text-sm font-semibold">
            Node results
          </h2>
          <p className="text-text-muted text-xs">
            {pluralize(succeeded, "completed", "completed")}
            {failed > 0 && ` · ${failed} failed`}
            {skipped > 0 && ` · ${skipped} skipped`}
          </p>
        </div>

        <ul className="border-border-base overflow-hidden rounded-md border">
          {data.node_runs.map((run) => (
            <NodeRunRow key={run.id} run={run} />
          ))}
        </ul>
      </section>

      <section aria-labelledby="run-data" className="space-y-3">
        <h2 id="run-data" className="text-text text-sm font-semibold">
          Run data
        </h2>
        <div className="grid gap-3 lg:grid-cols-2">
          <JsonView
            label="Trigger payload"
            value={data.trigger_payload}
            emptyText="The run started with no payload"
          />
          <JsonView
            label="Variables"
            value={data.variables}
            emptyText="No variables were set during this run"
          />
        </div>
      </section>
    </div>
  );
}

function Detail({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-text-subtle text-xs font-medium tracking-wide uppercase">{label}</dt>
      <dd className="mt-1">{children}</dd>
    </div>
  );
}
