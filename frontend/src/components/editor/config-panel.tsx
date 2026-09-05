"use client";

import { useMemo } from "react";
import { Trash2 } from "lucide-react";

import { KeyValueEditor } from "@/components/editor/key-value-editor";
import { Button } from "@/components/ui/button";
import { Field, Input, Select, Textarea } from "@/components/ui/field";
import type { NodeField, NodeType, ValidationIssue } from "@/lib/types";

interface Props {
  nodeId: string;
  label: string;
  configuration: Record<string, unknown>;
  definition: NodeType | undefined;
  issues: ValidationIssue[];
  onLabelChange: (label: string) => void;
  onConfigurationChange: (configuration: Record<string, unknown>) => void;
  onDelete: () => void;
}

/**
 * Renders a form from the node type's declared fields, so a node added on the
 * server is configurable here without any client change.
 */
export function ConfigPanel({
  nodeId,
  label,
  configuration,
  definition,
  issues,
  onLabelChange,
  onConfigurationChange,
  onDelete,
}: Props) {
  const errorsByField = useMemo(() => {
    const map = new Map<string, string>();
    for (const issue of issues) {
      if (issue.field && !map.has(issue.field)) map.set(issue.field, stripNodeName(issue.message));
    }
    return map;
  }, [issues]);

  const generalIssues = issues.filter((issue) => !issue.field);

  function update(key: string, value: unknown) {
    onConfigurationChange({ ...configuration, [key]: value });
  }

  const visibleFields = (definition?.fields ?? []).filter((field) =>
    isFieldVisible(field, configuration),
  );

  return (
    <div className="flex h-full flex-col">
      <header className="border-border-base border-b px-3 py-2.5">
        <h2 className="text-text-subtle text-xs font-semibold tracking-wide uppercase">
          {definition?.name ?? "Unknown node"}
        </h2>
        {definition?.description && (
          <p className="text-text-muted mt-1 text-xs">{definition.description}</p>
        )}
      </header>

      <div className="flex-1 scrollbar-thin space-y-4 overflow-y-auto p-3">
        {!definition && (
          <p
            role="alert"
            className="border-danger/30 bg-danger-soft text-danger rounded border p-2 text-xs"
          >
            This node type is not installed on the server, so it cannot be configured or run.
          </p>
        )}

        {generalIssues.map((issue) => (
          <p
            key={issue.message}
            role="alert"
            className="border-danger/30 bg-danger-soft text-danger rounded border p-2 text-xs"
          >
            {stripNodeName(issue.message)}
          </p>
        ))}

        <Field label="Label" hint="Shown on the canvas and in run history." required>
          <Input
            key={`${nodeId}-label`}
            defaultValue={label}
            maxLength={120}
            onChange={(event) => onLabelChange(event.target.value)}
          />
        </Field>

        {visibleFields.map((field) => (
          <ConfigField
            key={`${nodeId}-${field.key}`}
            field={field}
            value={configuration[field.key]}
            error={errorsByField.get(field.key)}
            onChange={(value) => update(field.key, value)}
          />
        ))}

        {definition && visibleFields.length === 0 && (
          <p className="text-text-subtle text-xs">This node has nothing to configure.</p>
        )}
      </div>

      <footer className="border-border-base border-t p-3">
        <Button
          variant="ghost"
          size="sm"
          className="text-danger w-full justify-center"
          onClick={onDelete}
        >
          <Trash2 aria-hidden className="h-3.5 w-3.5" />
          Delete node
        </Button>
      </footer>
    </div>
  );
}

function ConfigField({
  field,
  value,
  error,
  onChange,
}: {
  field: NodeField;
  value: unknown;
  error?: string;
  onChange: (value: unknown) => void;
}) {
  const hint = [field.help_text, field.supports_expressions ? "Supports {{ expressions }}." : ""]
    .filter(Boolean)
    .join(" ");

  switch (field.control) {
    case "select":
      return (
        <Field label={field.label} hint={hint} error={error} required={field.required}>
          <Select
            value={String(value ?? field.default ?? "")}
            onChange={(event) => onChange(event.target.value)}
          >
            {field.options.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
        </Field>
      );

    case "boolean":
      return (
        <label className="flex items-start gap-2">
          <input
            type="checkbox"
            checked={Boolean(value ?? field.default)}
            onChange={(event) => onChange(event.target.checked)}
            className="mt-0.5 h-3.5 w-3.5 accent-[var(--accent)]"
          />
          <span>
            <span className="text-text block text-xs font-medium">{field.label}</span>
            {hint && <span className="text-text-subtle block text-xs">{hint}</span>}
          </span>
        </label>
      );

    case "number":
      return (
        <Field label={field.label} hint={hint} error={error} required={field.required}>
          <Input
            type="number"
            step="any"
            // Falls back to the declared default so a field added after this
            // node was created still shows the value the server will apply.
            value={numberValue(value, field.default)}
            placeholder={field.placeholder}
            onChange={(event) => {
              const parsed = Number(event.target.value);
              onChange(event.target.value === "" || Number.isNaN(parsed) ? undefined : parsed);
            }}
          />
        </Field>
      );

    case "key_value":
      return (
        <Field label={field.label} hint={hint} error={error} required={field.required}>
          <KeyValueEditor
            label={field.label}
            value={(value ?? {}) as Record<string, string>}
            onChange={onChange}
          />
        </Field>
      );

    case "code":
      // One entry per line, which is how switch cases are edited.
      return (
        <Field label={field.label} hint={hint} error={error} required={field.required}>
          <Textarea
            rows={4}
            value={Array.isArray(value) ? (value as string[]).join("\n") : String(value ?? "")}
            placeholder={field.placeholder}
            className="font-mono text-xs"
            onChange={(event) =>
              onChange(event.target.value.split("\n").filter((line) => line.trim() !== ""))
            }
          />
        </Field>
      );

    case "json":
      return (
        <Field label={field.label} hint={hint} error={error} required={field.required}>
          <Textarea
            rows={6}
            value={String(value ?? "")}
            placeholder={field.placeholder}
            spellCheck={false}
            className="font-mono text-xs"
            onChange={(event) => onChange(event.target.value)}
          />
        </Field>
      );

    case "textarea":
      return (
        <Field label={field.label} hint={hint} error={error} required={field.required}>
          <Textarea
            rows={3}
            value={String(value ?? "")}
            placeholder={field.placeholder}
            onChange={(event) => onChange(event.target.value)}
          />
        </Field>
      );

    default:
      return (
        <Field label={field.label} hint={hint} error={error} required={field.required}>
          <Input
            value={String(value ?? "")}
            placeholder={field.placeholder}
            spellCheck={false}
            onChange={(event) => onChange(event.target.value)}
          />
        </Field>
      );
  }
}

function numberValue(value: unknown, fallback: unknown): string {
  const resolved = value ?? fallback;
  return resolved === undefined || resolved === null ? "" : String(resolved);
}

/** A field with `depends_on` only applies to some values of another field. */
function isFieldVisible(field: NodeField, configuration: Record<string, unknown>): boolean {
  if (!field.depends_on) return true;
  return field.depends_on_values.includes(String(configuration[field.depends_on] ?? ""));
}

/** Validation messages are prefixed with the node label, which the panel already shows. */
function stripNodeName(message: string): string {
  const separator = message.indexOf(": ");
  return separator > 0 ? message.slice(separator + 2) : message;
}
