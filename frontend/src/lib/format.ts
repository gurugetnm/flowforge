/** Presentation helpers shared across the app. */

const RELATIVE = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
const ABSOLUTE = new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" });

const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["year", 365 * 24 * 60 * 60_000],
  ["month", 30 * 24 * 60 * 60_000],
  ["day", 24 * 60 * 60_000],
  ["hour", 60 * 60_000],
  ["minute", 60_000],
  ["second", 1000],
];

/** "3 minutes ago", falling back to "just now" for very recent timestamps. */
export function relativeTime(iso: string | null): string {
  if (!iso) return "—";
  const elapsed = new Date(iso).getTime() - Date.now();

  for (const [unit, size] of UNITS) {
    if (Math.abs(elapsed) >= size) {
      return RELATIVE.format(Math.round(elapsed / size), unit);
    }
  }
  return "just now";
}

export function absoluteTime(iso: string | null): string {
  return iso ? ABSOLUTE.format(new Date(iso)) : "—";
}

/** Durations read as "820ms", "1.4s" or "2m 05s". */
export function duration(ms: number | null): string {
  if (ms === null || ms === undefined) return "—";
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`;

  const minutes = Math.floor(ms / 60_000);
  const seconds = Math.round((ms % 60_000) / 1000);
  return `${minutes}m ${String(seconds).padStart(2, "0")}s`;
}

/** Pretty-print a JSON value for display, never throwing on odd input. */
export function formatJson(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2) ?? String(value);
  } catch {
    return String(value);
  }
}

export function pluralize(count: number, singular: string, plural = `${singular}s`): string {
  return `${count} ${count === 1 ? singular : plural}`;
}
