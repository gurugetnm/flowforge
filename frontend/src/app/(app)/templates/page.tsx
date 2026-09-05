"use client";

import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";

import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { SkeletonRows } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { catalogApi } from "@/lib/api/catalog";
import { pluralize } from "@/lib/format";
import { queryKeys } from "@/lib/queries";

export default function TemplatesPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { notify } = useToast();

  const { data, isPending, error, refetch } = useQuery({
    queryKey: queryKeys.templates,
    queryFn: catalogApi.templates,
  });

  const create = useMutation({
    mutationFn: (templateId: string) => catalogApi.createFromTemplate(templateId),
    onSuccess: async (workflow) => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.workflows() });
      notify(`Created "${workflow.name}".`, "success");
      router.push(`/workflows/${workflow.id}`);
    },
    onError: () => notify("Could not create the workflow.", "error"),
  });

  return (
    <div className="mx-auto max-w-4xl space-y-5 p-4 sm:p-6">
      <PageHeader
        title="Templates"
        description="Working examples you can run straight away, then edit."
      />

      {isPending ? (
        <SkeletonRows rows={3} />
      ) : error ? (
        <ErrorState error={error} onRetry={() => void refetch()} />
      ) : data.length === 0 ? (
        <EmptyState
          icon={Sparkles}
          title="No templates available"
          description="Templates ship with the server. Check that the API is up to date."
        />
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2">
          {data.map((template) => (
            <li
              key={template.id}
              className="border-border-base bg-surface-raised flex flex-col rounded-md border p-4"
            >
              <h2 className="text-text text-sm font-medium">{template.name}</h2>
              <p className="text-text-muted mt-1 flex-1 text-sm">{template.description}</p>
              <p className="text-text-subtle mt-3 font-mono text-xs">
                {pluralize(template.node_count, "node")} · {template.node_types.join(" → ")}
              </p>
              <Button
                variant="primary"
                size="sm"
                className="mt-3 self-start"
                loading={create.isPending && create.variables === template.id}
                onClick={() => create.mutate(template.id)}
              >
                Use this template
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
