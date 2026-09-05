"use client";

import { Component, type ReactNode } from "react";

import { Button } from "@/components/ui/button";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

/**
 * Catches render errors so one broken panel does not blank the whole app.
 * Route level failures are handled by Next.js `error.tsx` files instead.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  render() {
    if (!this.state.error) return this.props.children;

    return (
      <div
        role="alert"
        className="border-danger/30 bg-danger-soft rounded-md border px-4 py-6 text-center"
      >
        <p className="text-text text-sm font-medium">This section failed to render.</p>
        <p className="text-text-muted mt-1 text-sm">{this.state.error.message}</p>
        <Button className="mt-3" onClick={() => this.setState({ error: null })}>
          Try again
        </Button>
      </div>
    );
  }
}
