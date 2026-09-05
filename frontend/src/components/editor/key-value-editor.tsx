"use client";

import { useState } from "react";
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

type Row = [key: string, value: string];

/**
 * Edits a string map as rows of inputs.
 *
 * Rows are held locally as an ordered list rather than derived from the map on
 * every render: a new row starts with a blank name, and a map cannot hold one,
 * so deriving would delete the row the moment it appeared. Only rows with a
 * name are reported upwards.
 */
export function KeyValueEditor({
  value,
  onChange,
  keyPlaceholder = "Name",
  valuePlaceholder = "Value",
  label,
}: Props) {
  const [rows, setRows] = useState<Row[]>(() => Object.entries(value ?? {}));

  function apply(next: Row[]) {
    setRows(next);
    onChange(Object.fromEntries(next.filter(([key]) => key.trim() !== "")));
  }

  function updateRow(index: number, row: Row) {
    apply(rows.map((existing, position) => (position === index ? row : existing)));
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
                className="h-8 min-w-0 flex-1 font-mono text-xs"
                onChange={(event) => updateRow(index, [event.target.value, entryValue])}
              />
              <Input
                value={entryValue}
                aria-label={`${label} value ${index + 1}`}
                placeholder={valuePlaceholder}
                className="h-8 min-w-0 flex-1 font-mono text-xs"
                onChange={(event) => updateRow(index, [key, event.target.value])}
              />
              <Button
                variant="ghost"
                size="icon"
                aria-label={`Remove ${key || `${label} ${index + 1}`}`}
                onClick={() => apply(rows.filter((_, position) => position !== index))}
              >
                <X aria-hidden className="h-3.5 w-3.5" />
              </Button>
            </li>
          ))}
        </ul>
      )}

      <Button size="sm" onClick={() => apply([...rows, ["", ""]])}>
        <Plus aria-hidden className="h-3 w-3" />
        Add {label.toLowerCase()}
      </Button>
    </div>
  );
}
