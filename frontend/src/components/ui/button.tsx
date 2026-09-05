"use client";

import { forwardRef } from "react";
import { Loader2 } from "lucide-react";

import { cn } from "@/lib/cn";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md" | "icon";

const VARIANTS: Record<ButtonVariant, string> = {
  primary: "bg-accent text-accent-fg hover:bg-accent-hover border border-transparent",
  secondary:
    "bg-surface-raised text-text border border-border-base hover:border-border-strong hover:bg-surface",
  ghost:
    "bg-transparent text-text-muted hover:bg-surface hover:text-text border border-transparent",
  danger: "bg-danger text-white hover:bg-danger-hover border border-transparent",
};

const SIZES: Record<ButtonSize, string> = {
  sm: "h-7 px-2.5 text-xs gap-1.5",
  md: "h-9 px-3.5 text-sm gap-2",
  icon: "h-8 w-8 justify-center",
};

/**
 * Button styling as class names, so an anchor or a `next/link` can look like a
 * button without being wrapped in one.
 */
export function buttonClasses(
  variant: ButtonVariant = "secondary",
  size: ButtonSize = "md",
  className?: string,
): string {
  return cn(
    "inline-flex items-center rounded-md font-medium transition-colors",
    "disabled:pointer-events-none disabled:opacity-50",
    VARIANTS[variant],
    SIZES[size],
    className,
  );
}

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant = "secondary", size = "md", loading = false, disabled, children, ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={buttonClasses(variant, size, className)}
      {...props}
    >
      {loading && <Loader2 aria-hidden className="h-3.5 w-3.5 animate-spin motion-reduce:hidden" />}
      {children}
    </button>
  );
});
