"use client";

import { use } from "react";

import { WorkflowEditor } from "@/components/editor/workflow-editor";

export default function WorkflowEditorPage({
  params,
}: {
  params: Promise<{ workflowId: string }>;
}) {
  const { workflowId } = use(params);
  return <WorkflowEditor workflowId={workflowId} />;
}
