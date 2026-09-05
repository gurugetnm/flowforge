"use client";

import { useMemo, useState } from "react";
import { Search } from "lucide-react";

import { Input } from "@/components/ui/field";
import type { NodeCategory, NodeType } from "@/lib/types";

const CATEGORY_ORDER: NodeCategory[] = ["trigger", "action", "logic", "data"];

const CATEGORY_LABELS: Record<NodeCategory, string> = {
  trigger: "Triggers",
  action: "Actions",
  logic: "Logic",
  data: "Data",
};

interface Props {
  nodeTypes: NodeType[];
  onAdd: (nodeType: NodeType) => void;
}

/**
 * The palette lists everything the server has installed. Nodes are added by
 * dragging onto the canvas or, for keyboard users, by activating the button.
 */
export function NodePalette({ nodeTypes, onAdd }: Props) {
  const [query, setQuery] = useState("");

  const grouped = useMemo(() => {
    const term = query.trim().toLowerCase();
    const matches = term
      ? nodeTypes.filter(
          (node) =>
            node.name.toLowerCase().includes(term) ||
            node.description.toLowerCase().includes(term) ||
            node.type.includes(term),
        )
      : nodeTypes;

    return CATEGORY_ORDER.map((category) => ({
      category,
      nodes: matches.filter((node) => node.category === category),
    })).filter((group) => group.nodes.length > 0);
  }, [nodeTypes, query]);

  return (
    <div className="flex h-full flex-col">
      <div className="border-border-base border-b p-2">
        <div className="relative">
          <Search
            aria-hidden
            className="text-text-subtle pointer-events-none absolute top-1/2 left-2.5 h-3.5 w-3.5 -translate-y-1/2"
          />
          <Input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search nodes"
            aria-label="Search node types"
            className="h-8 pl-8 text-xs"
          />
        </div>
      </div>

      <div className="flex-1 scrollbar-thin overflow-y-auto p-2">
        {grouped.length === 0 ? (
          <p className="text-text-subtle px-1 py-4 text-center text-xs">
            No node types match “{query}”.
          </p>
        ) : (
          grouped.map(({ category, nodes }) => (
            <section key={category} className="mb-3 last:mb-0">
              <h3 className="text-text-subtle px-1 pb-1 text-[11px] font-medium tracking-wide uppercase">
                {CATEGORY_LABELS[category]}
              </h3>
              <ul className="space-y-1">
                {nodes.map((node) => (
                  <li key={node.type}>
                    <button
                      type="button"
                      draggable
                      onDragStart={(event) => {
                        event.dataTransfer.setData("application/flowforge-node", node.type);
                        event.dataTransfer.effectAllowed = "move";
                      }}
                      onClick={() => onAdd(node)}
                      title={node.description}
                      className="border-border-base bg-surface-raised hover:border-border-strong hover:bg-surface w-full cursor-grab rounded border px-2 py-1.5 text-left transition-colors active:cursor-grabbing"
                    >
                      <span className="text-text block text-xs font-medium">{node.name}</span>
                      <span className="text-text-muted mt-0.5 line-clamp-2 block text-[11px] leading-snug">
                        {node.description}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          ))
        )}
      </div>

      <p className="border-border-base text-text-subtle border-t px-3 py-2 text-[11px]">
        Drag a node onto the canvas, or click to add it.
      </p>
    </div>
  );
}
