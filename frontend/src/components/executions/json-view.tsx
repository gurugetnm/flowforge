"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";

import { Button } from "@/components/ui/button";
import { formatJson } from "@/lib/format";

interface Props {
  label: string;
  value: unknown;
  emptyText?: string;
}

const COPY_FEEDBACK_MS = 1500;

/** A labelled, copyable JSON block used throughout the execution inspector. */
export function JsonView({ label, value, emptyText = "No data" }: Props) {
  const [copied, setCopied] = useState(false);

  const isEmpty =
    value === null ||
    value === undefined ||
    (typeof value === "object" && Object.keys(value as object).length === 0);
  const text = formatJson(value);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), COPY_FEEDBACK_MS);
    } catch {
      // Clipboard access can be denied; the text is still selectable.
    }
  }

  return (
    <div className="min-w-0">
      <div className="flex items-center justify-between gap-2">
        <h4 className="text-text-subtle text-xs font-medium tracking-wide uppercase">{label}</h4>
        {!isEmpty && (
          <Button variant="ghost" size="sm" onClick={() => void copy()}>
            {copied ? (
              <Check aria-hidden className="h-3 w-3" />
            ) : (
              <Copy aria-hidden className="h-3 w-3" />
            )}
            {copied ? "Copied" : "Copy"}
          </Button>
        )}
      </div>
      {isEmpty ? (
        <p className="text-text-subtle mt-1 text-sm">{emptyText}</p>
      ) : (
        <pre className="border-border-base bg-surface text-text mt-1 max-h-72 scrollbar-thin overflow-auto rounded border p-2.5 font-mono text-xs leading-relaxed">
          {text}
        </pre>
      )}
    </div>
  );
}
