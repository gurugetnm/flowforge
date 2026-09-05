"use client";

import { createContext, forwardRef, useContext, useId } from "react";

import { cn } from "@/lib/cn";

const CONTROL_CLASSES = cn(
  "w-full rounded-md border border-border-base bg-surface-raised px-2.5 py-1.5 text-sm",
  "text-text placeholder:text-text-subtle",
  "focus:border-accent focus:outline-none",
  "disabled:opacity-60",
  "aria-[invalid=true]:border-danger",
);

interface FieldContextValue {
  id: string;
  describedBy?: string;
  invalid: boolean;
}

const FieldContext = createContext<FieldContextValue | null>(null);

/**
 * Accessibility props a control inherits from its surrounding `Field`, so
 * every input is labelled and its error is announced without the caller
 * wiring up ids by hand. Props passed directly to the control still win.
 */
function useFieldProps() {
  const context = useContext(FieldContext);
  if (!context) return {};
  return {
    id: context.id,
    "aria-describedby": context.describedBy,
    "aria-invalid": context.invalid || undefined,
  };
}

export const Input = forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...props }, ref) {
    return (
      <input ref={ref} {...useFieldProps()} className={cn(CONTROL_CLASSES, className)} {...props} />
    );
  },
);

export const Textarea = forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(function Textarea({ className, ...props }, ref) {
  return (
    <textarea
      ref={ref}
      {...useFieldProps()}
      className={cn(CONTROL_CLASSES, "resize-y", className)}
      {...props}
    />
  );
});

export const Select = forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(
  function Select({ className, ...props }, ref) {
    return (
      <select
        ref={ref}
        {...useFieldProps()}
        className={cn(CONTROL_CLASSES, "pr-8", className)}
        {...props}
      />
    );
  },
);

interface FieldProps {
  label: string;
  hint?: string;
  error?: string;
  required?: boolean;
  children: React.ReactNode;
  className?: string;
}

/** A labelled control with an optional hint and an error that replaces it. */
export function Field({ label, hint, error, required, children, className }: FieldProps) {
  const id = useId();
  const describedBy = error ? `${id}-error` : hint ? `${id}-hint` : undefined;

  return (
    <div className={cn("space-y-1.5", className)}>
      <label htmlFor={id} className="text-text block text-xs font-medium">
        {label}
        {required && (
          <span className="text-danger ml-1" aria-hidden>
            *
          </span>
        )}
      </label>
      <FieldContext.Provider value={{ id, describedBy, invalid: Boolean(error) }}>
        {children}
      </FieldContext.Provider>
      {error ? (
        <p id={`${id}-error`} role="alert" className="text-danger text-xs">
          {error}
        </p>
      ) : hint ? (
        <p id={`${id}-hint`} className="text-text-subtle text-xs">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
