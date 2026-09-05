import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-3 px-4 text-center">
      <p className="text-text-subtle font-mono text-xs">404</p>
      <h1 className="text-text text-lg font-semibold">This page does not exist</h1>
      <p className="text-text-muted max-w-sm text-sm">
        The page you were looking for may have been moved or deleted.
      </p>
      <Link href="/dashboard" className="text-accent mt-2 text-sm font-medium hover:underline">
        Back to the dashboard
      </Link>
    </div>
  );
}
