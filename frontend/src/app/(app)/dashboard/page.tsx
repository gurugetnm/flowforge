"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Activity, CheckCircle2, GitBranch, XCircle } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { PageHeader } from "@/components/layout/page-header";
import { buttonClasses } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { SkeletonRows } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/ui/status-badge";
import { catalogApi } from "@/lib/api/catalog";
import { duration, relativeTime } from "@/lib/format";
import { queryKeys } from "@/lib/queries";

export default function DashboardPage() {
  const { data, isPending, error, refetch } = useQuery({
    queryKey: queryKeys.overview,
    queryFn: catalogApi.overview,
  });

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-4 sm:p-6">
      <PageHeader
        title="Dashboard"
        description="Your workflows and their most recent runs."
        actions={
          <Link href="/workflows" className={buttonClasses("primary")}>
            Go to workflows
          </Link>
        }
      />

      {isPending ? (
        <SkeletonRows rows={3} />
      ) : error ? (
        <ErrorState error={error} onRetry={() => void refetch()} />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <StatCard label="Workflows" value={data.workflow_count} icon={GitBranch} />
            <StatCard label="Active" value={data.active_workflow_count} icon={Activity} />
            <StatCard
              label="Successful runs"
              value={data.execution_counts.succeeded ?? 0}
              icon={CheckCircle2}
              tone="success"
            />
            <StatCard
              label="Failed runs"
              value={data.execution_counts.failed ?? 0}
              icon={XCircle}
              tone="danger"
            />
          </div>

          <section aria-labelledby="recent-runs" className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 id="recent-runs" className="text-text text-sm font-semibold">
                Recent runs
              </h2>
              <Link href="/executions" className="text-accent text-sm hover:underline">
                View all
              </Link>
            </div>

            {data.recent_executions.length === 0 ? (
              <EmptyState
                icon={Activity}
                title="No runs yet"
                description="Build a workflow and run it to see the results here."
                action={
                  <Link
                    href="/workflows"
                    className="text-accent text-sm font-medium hover:underline"
                  >
                    Create a workflow
                  </Link>
                }
              />
            ) : (
              <ul className="divide-border-base border-border-base divide-y rounded-md border">
                {data.recent_executions.map((execution) => (
                  <li key={execution.id}>
                    <Link
                      href={`/executions/${execution.id}`}
                      className="hover:bg-surface flex items-center justify-between gap-3 px-4 py-3 transition-colors"
                    >
                      <div className="min-w-0">
                        <p className="text-text truncate text-sm font-medium">
                          {execution.workflow_name}
                        </p>
                        <p className="text-text-muted mt-0.5 text-xs">
                          {relativeTime(execution.started_at)} · {duration(execution.duration_ms)}
                        </p>
                      </div>
                      <StatusBadge status={execution.status} />
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  icon: Icon,
  tone = "default",
}: {
  label: string;
  value: number;
  icon: LucideIcon;
  tone?: "default" | "success" | "danger";
}) {
  const toneClass =
    tone === "success" ? "text-success" : tone === "danger" ? "text-danger" : "text-text-subtle";

  return (
    <div className="border-border-base bg-surface-raised rounded-md border p-4">
      <div className="flex items-center justify-between">
        <p className="text-text-muted text-xs font-medium">{label}</p>
        <Icon aria-hidden className={`h-4 w-4 ${toneClass}`} />
      </div>
      <p className="text-text mt-2 font-mono text-2xl font-semibold tabular-nums">{value}</p>
    </div>
  );
}
