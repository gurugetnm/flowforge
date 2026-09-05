"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field, Input, Textarea } from "@/components/ui/field";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api";
import { workflowsApi } from "@/lib/api/workflows";
import { queryKeys } from "@/lib/queries";
import { fieldErrors, workflowSchema } from "@/lib/validation";

interface Props {
  open: boolean;
  onClose: () => void;
}

export function CreateWorkflowDialog({ open, onClose }: Props) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { notify } = useToast();
  const [errors, setErrors] = useState<Record<string, string>>({});

  const create = useMutation({
    mutationFn: workflowsApi.create,
    onSuccess: async (workflow) => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.workflows() });
      notify(`Created "${workflow.name}".`, "success");
      onClose();
      router.push(`/workflows/${workflow.id}`);
    },
    onError: (error) => {
      notify(error instanceof ApiError ? error.message : "Could not create the workflow.", "error");
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
    create.mutate(parsed.data);
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="New workflow"
      description="Start from an empty canvas. You can rename it at any time."
    >
      <form id="create-workflow" onSubmit={handleSubmit} noValidate className="space-y-4">
        <Field label="Name" error={errors.name} required>
          <Input name="name" placeholder="Nightly sync" autoFocus maxLength={120} />
        </Field>
        <Field label="Description" error={errors.description} hint="Optional.">
          <Textarea
            name="description"
            rows={3}
            maxLength={2000}
            placeholder="What this workflow does and when it runs."
          />
        </Field>
        <div className="flex justify-end gap-2 pt-1">
          <Button type="button" onClick={onClose} disabled={create.isPending}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" loading={create.isPending}>
            Create workflow
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
