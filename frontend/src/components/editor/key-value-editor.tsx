"use client";

import { Plus, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/field";

interface Props {
  value: Record<string, string>;
  onChange: (value: Record<string, string>) => void;
  keyPlaceholder?: string;
  valuePlaceholder?: string;
  label: string;
}

/**
 * Edits a string map as rows of inputs.
 *
 * Rows are held as an array while editing so a half-typed key does not collide
 * with another row or vanish as it is retyped.
 */
export function KeyValueEditor({
  value,
  onChange,
  keyPlaceholder = "Name",
  valuePlaceholder = "Value",
  label,
}: Props) {
  const rows = Object.entries(value ?? {});

  function emit(next: [string, string][]) {
    onChange(Object.fromEntries(next.filter(([key]) => key.trim() !== "")));
  }

  return (
    <div className="space-y-1.5">
      {rows.length > 0 && (
        <ul className="space-y-1.5">
          {rows.map(([key, entryValue], index) => (
            <li key={index} className="flex items-center gap-1.5">
              <Input
                value={key}
                aria-label={`${label} name ${index + 1}`}
                placeholder={keyPlaceholder}
                className="h-8 flex-1 font-mono text-xs"
                onChange={(event) => {
                  const next = [...rows] as [string, string][];
                  next[index] = [event.target.value, entryValue];
                  emit(next);
                }}
              />
              <Input
                value={entryValue}
                aria-label={`${label} value ${index + 1}`}
                placeholder={valuePlaceholder}
                className="h-8 flex-1 font-mono text-xs"
                onChange={(event) => {
                  const next = [...rows] as [string, string][];
                  next[index] = [key, event.target.value];
                  emit(next);
                }}
              />
              <Button
                variant="ghost"
                size="icon"
                aria-label={`Remove ${key || `${label} ${index + 1}`}`}
                onClick={() => emit(rows.filter((_, position) => position !== index))}
              >
                <X aria-hidden className="h-3.5 w-3.5" />
              </Button>
            </li>
          ))}
        </ul>
      )}

      <Button size="sm" onClick={() => emit([...rows, ["", ""]] as [string, string][])}>
        <Plus aria-hidden className="h-3 w-3" />
        Add {label.toLowerCase()}
      </Button>
    </div>
  );
}
