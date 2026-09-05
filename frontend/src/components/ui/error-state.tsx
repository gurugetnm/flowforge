"use client";

import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";

interface ErrorStateProps {
  error: unknown;
  onRetry?: () => void;
  title?: string;
}

/** Renders an API failure with the server's message rather than a stack trace. */
export function ErrorState({ error, onRetry, title = "Something went wrong" }: ErrorStateProps) {
  const message =
    error instanceof ApiError
      ? error.message
      : error instanceof Error
        ? "The server could not be reached. Check that the API is running."
        : "An unexpected error occurred.";

  return (
    <div
      role="alert"
      className="border-danger/30 bg-danger-soft flex flex-col items-center rounded-md border px-6 py-10 text-center"
    >
      <AlertTriangle aria-hidden className="text-danger h-5 w-5" />
      <h3 className="text-text mt-3 text-sm font-medium">{title}</h3>
      <p className="text-text-muted mt-1 max-w-md text-sm">{message}</p>
      {onRetry && (
        <Button className="mt-4" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}
