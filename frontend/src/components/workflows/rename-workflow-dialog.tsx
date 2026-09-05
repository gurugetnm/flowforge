"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input, Textarea } from "@/components/ui/field";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api";
import { workflowsApi } from "@/lib/api/workflows";
import { queryKeys } from "@/lib/queries";
import type { WorkflowSummary } from "@/lib/types";
import { fieldErrors, workflowSchema } from "@/lib/validation";

interface Props {
  workflow: WorkflowSummary | null;
  onClose: () => void;
}

export function RenameWorkflowDialog({ workflow, onClose }: Props) {
  const queryClient = useQueryClient();
  const { notify } = useToast();
  const [errors, setErrors] = useState<Record<string, string>>({});

  const update = useMutation({
    mutationFn: (values: { name: string; description: string }) =>
      workflowsApi.update(workflow!.id, values),
    onSuccess: async (updated) => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.workflows() });
      await queryClient.invalidateQueries({ queryKey: queryKeys.workflow(updated.id) });
      notify("Workflow updated.", "success");
      onClose();
    },
    onError: (error) => {
      notify(error instanceof ApiError ? error.message : "Could not save the changes.", "error");
    },
  });

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const parsed = workflowSchema.safeParse(Object.fromEntries(new FormData(event.currentTarget)));

    if (!parsed.success) {
      setErrors(fieldErrors(parsed.error));
      return;
    }
    setErrors({});
    update.mutate(parsed.data);
  }

  return (
    <Dialog open={workflow !== null} onClose={onClose} title="Rename workflow">
      {workflow && (
        <form key={workflow.id} onSubmit={handleSubmit} noValidate className="space-y-4">
          <Field label="Name" error={errors.name} required>
            <Input name="name" defaultValue={workflow.name} autoFocus maxLength={120} />
          </Field>
          <Field label="Description" error={errors.description}>
            <Textarea
              name="description"
              rows={3}
              maxLength={2000}
              defaultValue={workflow.description}
            />
          </Field>
          <div className="flex justify-end gap-2 pt-1">
            <Button type="button" onClick={onClose} disabled={update.isPending}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={update.isPending}>
              Save changes
            </Button>
          </div>
        </form>
      )}
    </Dialog>
  );
}
