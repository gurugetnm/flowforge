"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  addEdge,
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
  type Connection,
  type OnConnect,
} from "@xyflow/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ConfigPanel } from "@/components/editor/config-panel";
import { WorkflowFlowNode } from "@/components/editor/flow-node";
import {
  graphFingerprint,
  toApiGraph,
  toFlowEdges,
  toFlowNodes,
  type FlowEdge,
  type FlowNode,
} from "@/components/editor/graph-model";
import { NodePalette } from "@/components/editor/node-palette";
import { useEditorShortcuts } from "@/components/editor/use-editor-shortcuts";
import { ValidationPanel } from "@/components/editor/validation-panel";
import { EditorToolbar } from "@/components/editor/editor-toolbar";
import { ErrorState } from "@/components/ui/error-state";
import { SkeletonRows } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api";
import { catalogApi } from "@/lib/api/catalog";
import { executionsApi } from "@/lib/api/executions";
import { workflowsApi } from "@/lib/api/workflows";
import { queryKeys } from "@/lib/queries";
import type { NodeType, WorkflowGraph } from "@/lib/types";

import "@xyflow/react/dist/style.css";

const NODE_TYPES = { workflowNode: WorkflowFlowNode };
const NEW_NODE_OFFSET = 60;

export function WorkflowEditor({ workflowId }: { workflowId: string }) {
  return (
    <ReactFlowProvider>
      <EditorCanvas workflowId={workflowId} />
    </ReactFlowProvider>
  );
}

function EditorCanvas({ workflowId }: { workflowId: string }) {
  const queryClient = useQueryClient();
  const { notify } = useToast();
  const canvasRef = useRef<HTMLDivElement>(null);
  const { screenToFlowPosition } = useReactFlow();

  const [nodes, setNodes, onNodesChange] = useNodesState<FlowNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<FlowEdge>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  /** Fingerprint of the last saved graph, used for dirty-state detection. */
  const [savedFingerprint, setSavedFingerprint] = useState<string | null>(null);

  const workflowQuery = useQuery({
    queryKey: queryKeys.workflow(workflowId),
    queryFn: () => workflowsApi.get(workflowId),
  });

  const catalogQuery = useQuery({
    queryKey: queryKeys.nodeTypes,
    queryFn: catalogApi.nodeTypes,
    staleTime: 60 * 60_000,
  });

  const graphQuery = useQuery({
    queryKey: queryKeys.workflowGraph(workflowId),
    queryFn: () => workflowsApi.graph(workflowId),
  });

  const catalog = useMemo(
    () => new Map((catalogQuery.data ?? []).map((node) => [node.type, node])),
    [catalogQuery.data],
  );

  // Load the stored graph onto the canvas once both it and the catalog arrive.
  const loadedRef = useRef(false);
  useEffect(() => {
    if (loadedRef.current || !graphQuery.data || catalogQuery.data === undefined) return;
    loadedRef.current = true;

    setNodes(toFlowNodes(graphQuery.data, catalog));
    setEdges(toFlowEdges(graphQuery.data));
    setSavedFingerprint(graphFingerprint(graphQuery.data));
  }, [graphQuery.data, catalogQuery.data, catalog, setNodes, setEdges]);

  const currentGraph: WorkflowGraph = useMemo(() => toApiGraph(nodes, edges), [nodes, edges]);
  const isDirty = savedFingerprint !== null && graphFingerprint(currentGraph) !== savedFingerprint;

  const validationQuery = useQuery({
    queryKey: queryKeys.workflowValidation(workflowId),
    queryFn: () => workflowsApi.validate(workflowId),
    enabled: savedFingerprint !== null,
  });

  const invalidNodeIds = useMemo(
    () =>
      new Set(
        (validationQuery.data?.errors ?? [])
          .map((issue) => issue.node_id)
          .filter((id): id is string => id !== null),
      ),
    [validationQuery.data],
  );

  // Reflect validation errors on the canvas without rebuilding the graph.
  useEffect(() => {
    setNodes((current) =>
      current.map((node) =>
        node.data.hasError === invalidNodeIds.has(node.id)
          ? node
          : { ...node, data: { ...node.data, hasError: invalidNodeIds.has(node.id) } },
      ),
    );
  }, [invalidNodeIds, setNodes]);

  const save = useMutation({
    mutationFn: (graph: WorkflowGraph) => workflowsApi.saveGraph(workflowId, graph),
    onSuccess: async (saved) => {
      setSavedFingerprint(graphFingerprint(saved));
      queryClient.setQueryData(queryKeys.workflowGraph(workflowId), saved);
      await queryClient.invalidateQueries({ queryKey: queryKeys.workflowValidation(workflowId) });
      await queryClient.invalidateQueries({ queryKey: queryKeys.workflows() });
    },
    onError: (error) => {
      notify(error instanceof ApiError ? error.message : "Could not save the workflow.", "error");
    },
  });

  const run = useMutation({
    mutationFn: () => executionsApi.run(workflowId),
    onSuccess: async (execution) => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.executions() });
      // Colour each node by how it fared in this run.
      const outcomes = new Map(
        execution.node_runs
          .filter((nodeRun) => nodeRun.node_id)
          .map((nodeRun) => [nodeRun.node_id as string, nodeRun.status]),
      );
      setNodes((current) =>
        current.map((node) => ({
          ...node,
          data: {
            ...node.data,
            runStatus: outcomes.get(node.id) as FlowNode["data"]["runStatus"],
          },
        })),
      );
      notify(
        execution.status === "succeeded"
          ? "Run completed successfully."
          : `Run failed: ${execution.error ?? "see the execution for details"}.`,
        execution.status === "succeeded" ? "success" : "error",
      );
    },
    onError: (error) => {
      if (error instanceof ApiError && error.code === "workflow_invalid") {
        notify(`${error.message} Check the problems panel.`, "error");
        void validationQuery.refetch();
        return;
      }
      notify("Could not start the run.", "error");
    },
  });

  const handleSave = useCallback(() => {
    if (!save.isPending) save.mutate(toApiGraph(nodes, edges));
  }, [save, nodes, edges]);

  const handleRun = useCallback(() => {
    if (isDirty) {
      notify("Save your changes before running.", "info");
      return;
    }
    run.mutate();
  }, [isDirty, notify, run]);

  const deleteSelection = useCallback(() => {
    const selectedEdges = edges.filter((edge) => edge.selected);
    const selectedNodes = nodes.filter((node) => node.selected);
    if (selectedEdges.length === 0 && selectedNodes.length === 0) return;

    const removedIds = new Set(selectedNodes.map((node) => node.id));
    setNodes((current) => current.filter((node) => !removedIds.has(node.id)));
    setEdges((current) =>
      current.filter(
        (edge) => !edge.selected && !removedIds.has(edge.source) && !removedIds.has(edge.target),
      ),
    );
    if (selectedNodeId && removedIds.has(selectedNodeId)) setSelectedNodeId(null);
  }, [edges, nodes, selectedNodeId, setEdges, setNodes]);

  useEditorShortcuts({ onSave: handleSave, onRun: handleRun, onDelete: deleteSelection });

  // Warn before leaving with unsaved work.
  useEffect(() => {
    if (!isDirty) return;
    function warn(event: BeforeUnloadEvent) {
      event.preventDefault();
    }
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [isDirty]);

  const addNode = useCallback(
    (definition: NodeType, position?: { x: number; y: number }) => {
      const id = crypto.randomUUID();
      setNodes((current) => [
        ...current,
        {
          id,
          type: "workflowNode" as const,
          position: position ?? {
            x: NEW_NODE_OFFSET + current.length * 30,
            y: NEW_NODE_OFFSET + current.length * 30,
          },
          data: {
            label: definition.name,
            nodeType: definition.type,
            configuration: { ...definition.default_configuration },
            definition,
          },
        },
      ]);
      setSelectedNodeId(id);
    },
    [setNodes],
  );

  const onConnect: OnConnect = useCallback(
    (connection: Connection) => {
      setEdges((current) => addEdge({ ...connection, id: crypto.randomUUID() }, current));
    },
    [setEdges],
  );

  const updateSelectedNode = useCallback(
    (patch: Partial<FlowNode["data"]>) => {
      setNodes((current) =>
        current.map((node) =>
          node.id === selectedNodeId ? { ...node, data: { ...node.data, ...patch } } : node,
        ),
      );
    },
    [selectedNodeId, setNodes],
  );

  const selectedNode = nodes.find((node) => node.id === selectedNodeId) ?? null;
  const selectedIssues = useMemo(
    () =>
      [...(validationQuery.data?.errors ?? []), ...(validationQuery.data?.warnings ?? [])].filter(
        (issue) => issue.node_id === selectedNodeId,
      ),
    [validationQuery.data, selectedNodeId],
  );

  const loadError = workflowQuery.error ?? graphQuery.error ?? catalogQuery.error;
  if (loadError) {
    return (
      <div className="p-6">
        <ErrorState
          error={loadError}
          title={
            loadError instanceof ApiError && loadError.isNotFound ? "Workflow not found" : undefined
          }
          onRetry={() => {
            void workflowQuery.refetch();
            void graphQuery.refetch();
            void catalogQuery.refetch();
          }}
        />
      </div>
    );
  }

  const workflow = workflowQuery.data;
  const nodeTypes = catalogQuery.data;
  if (!workflow || !nodeTypes || !graphQuery.data) {
    return (
      <div className="p-6">
        <SkeletonRows rows={4} />
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <EditorToolbar
        workflow={workflow}
        hasWebhookTrigger={nodes.some((node) => node.data.nodeType === "webhook_trigger")}
        isDirty={isDirty}
        saving={save.isPending}
        running={run.isPending}
        validation={validationQuery.data}
        onSave={handleSave}
        onRun={handleRun}
      />

      <div className="flex min-h-0 flex-1">
        <div className="border-border-base bg-surface hidden w-56 shrink-0 border-r lg:block">
          <NodePalette nodeTypes={nodeTypes} onAdd={(definition) => addNode(definition)} />
        </div>

        <div
          ref={canvasRef}
          className="relative min-w-0 flex-1"
          onDragOver={(event) => {
            event.preventDefault();
            event.dataTransfer.dropEffect = "move";
          }}
          onDrop={(event) => {
            event.preventDefault();
            const type = event.dataTransfer.getData("application/flowforge-node");
            const definition = catalog.get(type);
            if (!definition) return;
            addNode(definition, screenToFlowPosition({ x: event.clientX, y: event.clientY }));
          }}
        >
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={NODE_TYPES}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={(_, node) => setSelectedNodeId(node.id)}
            onPaneClick={() => setSelectedNodeId(null)}
            // Deletion is handled by the editor shortcut so it can also clear
            // the configuration panel.
            deleteKeyCode={null}
            fitView
            proOptions={{ hideAttribution: false }}
            className="bg-canvas"
          >
            <Background
              variant={BackgroundVariant.Dots}
              gap={16}
              size={1}
              color="var(--canvas-dot)"
            />
            <Controls showInteractive={false} className="!border-border-base !bg-surface-raised" />
            <MiniMap
              pannable
              zoomable
              className="!border-border-base !bg-surface !border"
              maskColor="rgb(0 0 0 / 0.06)"
            />
          </ReactFlow>
        </div>

        {selectedNode && (
          <aside className="border-border-base bg-surface hidden w-80 shrink-0 border-l xl:block">
            <ConfigPanel
              nodeId={selectedNode.id}
              label={selectedNode.data.label}
              configuration={selectedNode.data.configuration}
              definition={selectedNode.data.definition}
              issues={selectedIssues}
              onLabelChange={(label) => updateSelectedNode({ label })}
              onConfigurationChange={(configuration) => updateSelectedNode({ configuration })}
              onDelete={() => {
                setNodes((current) => current.filter((node) => node.id !== selectedNode.id));
                setEdges((current) =>
                  current.filter(
                    (edge) => edge.source !== selectedNode.id && edge.target !== selectedNode.id,
                  ),
                );
                setSelectedNodeId(null);
              }}
            />
          </aside>
        )}
      </div>

      <div className="border-border-base bg-surface border-t">
        <ValidationPanel
          result={validationQuery.data}
          onSelectNode={(nodeId) => setSelectedNodeId(nodeId)}
        />
      </div>
    </div>
  );
}
