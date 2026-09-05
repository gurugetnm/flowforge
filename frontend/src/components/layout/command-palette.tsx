"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { GitBranch, LayoutDashboard, ListChecks, Search, Sparkles } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Input } from "@/components/ui/field";
import { workflowsApi } from "@/lib/api/workflows";
import { cn } from "@/lib/cn";
import { queryKeys } from "@/lib/queries";
import { useDebounced } from "@/lib/use-debounced";

interface Command {
  id: string;
  label: string;
  hint?: string;
  icon: LucideIcon;
  run: () => void;
}

const WORKFLOW_RESULT_LIMIT = 5;

/**
 * Cmd+K palette for jumping between pages and straight to a workflow.
 *
 * Rendered as a plain overlay rather than a `<dialog>` so the search input
 * keeps focus while the arrow keys move the selection.
 */
export function CommandPalette() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const debouncedQuery = useDebounced(query, 200);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen((value) => !value);
      }
      if (event.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const { data: matches } = useQuery({
    queryKey: queryKeys.workflows({ palette: debouncedQuery }),
    queryFn: () => workflowsApi.list({ search: debouncedQuery, limit: WORKFLOW_RESULT_LIMIT }),
    enabled: open,
  });

  const commands = useMemo<Command[]>(() => {
    const close = (path: string) => () => {
      setOpen(false);
      setQuery("");
      router.push(path);
    };

    const navigation: Command[] = [
      { id: "nav-dashboard", label: "Dashboard", icon: LayoutDashboard, run: close("/dashboard") },
      { id: "nav-workflows", label: "Workflows", icon: GitBranch, run: close("/workflows") },
      { id: "nav-executions", label: "Executions", icon: ListChecks, run: close("/executions") },
      { id: "nav-templates", label: "Templates", icon: Sparkles, run: close("/templates") },
    ];

    const term = debouncedQuery.trim().toLowerCase();
    const filteredNavigation = term
      ? navigation.filter((command) => command.label.toLowerCase().includes(term))
      : navigation;

    const workflows: Command[] = (matches?.items ?? []).map((workflow) => ({
      id: workflow.id,
      label: workflow.name,
      hint: "Open in the editor",
      icon: GitBranch,
      run: close(`/workflows/${workflow.id}`),
    }));

    return [...filteredNavigation, ...workflows];
  }, [debouncedQuery, matches, router]);

  const selected = commands[Math.min(activeIndex, commands.length - 1)];

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/40 p-4 pt-[12vh]"
      onClick={(event) => {
        if (event.target === event.currentTarget) setOpen(false);
      }}
    >
      <div
        role="dialog"
        aria-label="Command palette"
        aria-modal="true"
        className="border-border-base bg-surface-raised w-full max-w-lg overflow-hidden rounded-lg border shadow-2xl"
        onKeyDown={(event) => {
          if (event.key === "ArrowDown") {
            event.preventDefault();
            setActiveIndex((index) => (index + 1) % Math.max(commands.length, 1));
          }
          if (event.key === "ArrowUp") {
            event.preventDefault();
            setActiveIndex(
              (index) => (index - 1 + Math.max(commands.length, 1)) % Math.max(commands.length, 1),
            );
          }
          if (event.key === "Enter" && selected) {
            event.preventDefault();
            selected.run();
          }
        }}
      >
        <div className="border-border-base flex items-center gap-2 border-b px-3">
          <Search aria-hidden className="text-text-subtle h-4 w-4 shrink-0" />
          <Input
            ref={inputRef}
            autoFocus
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setActiveIndex(0);
            }}
            placeholder="Search pages and workflows"
            aria-label="Search pages and workflows"
            className="border-0 bg-transparent py-3 focus:border-0"
          />
        </div>

        {commands.length === 0 ? (
          <p className="text-text-muted px-4 py-6 text-center text-sm">
            Nothing matches “{query}”.
          </p>
        ) : (
          <ul className="max-h-80 scrollbar-thin overflow-y-auto py-1">
            {commands.map((command, index) => (
              <li key={command.id}>
                <button
                  type="button"
                  onMouseEnter={() => setActiveIndex(index)}
                  onClick={command.run}
                  aria-current={index === activeIndex || undefined}
                  className={cn(
                    "flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm",
                    index === activeIndex ? "bg-accent-soft text-accent" : "text-text",
                  )}
                >
                  <command.icon aria-hidden className="h-4 w-4 shrink-0" />
                  <span className="flex-1 truncate">{command.label}</span>
                  {command.hint && (
                    <span className="text-text-subtle shrink-0 text-xs">{command.hint}</span>
                  )}
                </button>
              </li>
            ))}
          </ul>
        )}

        <p className="border-border-base text-text-subtle border-t px-3 py-2 text-xs">
          <kbd className="font-mono">↑</kbd> <kbd className="font-mono">↓</kbd> to move,{" "}
          <kbd className="font-mono">↵</kbd> to open, <kbd className="font-mono">esc</kbd> to close.
        </p>
      </div>
    </div>
  );
}
