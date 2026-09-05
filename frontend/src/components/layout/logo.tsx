import { cn } from "@/lib/cn";

/** The FlowForge mark: three nodes joined by two edges. */
export function Logo({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden
      className={cn("h-5 w-5", className)}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
    >
      <rect x="2.5" y="3" width="6" height="5" rx="1.5" />
      <rect x="15.5" y="8.5" width="6" height="5" rx="1.5" />
      <rect x="2.5" y="15" width="6" height="5" rx="1.5" />
      <path d="M8.5 5.5h3.5a1.5 1.5 0 0 1 1.5 1.5v2.5" />
      <path d="M15.5 12.5h-2.5a1.5 1.5 0 0 0-1.5 1.5v2a1.5 1.5 0 0 1-1.5 1.5H8.5" />
    </svg>
  );
}
