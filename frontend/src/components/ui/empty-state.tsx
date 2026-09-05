import type { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: React.ReactNode;
}

/** Shown when a list has no rows, explaining what to do next. */
export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="border-border-base flex flex-col items-center justify-center rounded-md border border-dashed px-6 py-14 text-center">
      <Icon aria-hidden className="text-text-subtle h-6 w-6" />
      <h3 className="text-text mt-3 text-sm font-medium">{title}</h3>
      <p className="text-text-muted mt-1 max-w-sm text-sm">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
