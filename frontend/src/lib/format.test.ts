import { describe, expect, it, vi, afterEach } from "vitest";

import { duration, formatJson, pluralize, relativeTime } from "@/lib/format";

describe("duration", () => {
  it("shows milliseconds below a second", () => {
    expect(duration(0)).toBe("0ms");
    expect(duration(820)).toBe("820ms");
  });

  it("shows seconds with one decimal below a minute", () => {
    expect(duration(1400)).toBe("1.4s");
    expect(duration(59_900)).toBe("59.9s");
  });

  it("shows minutes and padded seconds above a minute", () => {
    expect(duration(125_000)).toBe("2m 05s");
  });

  it("renders a dash when there is no duration", () => {
    expect(duration(null)).toBe("—");
  });
});

describe("relativeTime", () => {
  afterEach(() => vi.useRealTimers());

  it("describes recent timestamps in the largest sensible unit", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-01-01T12:00:00Z"));

    expect(relativeTime("2026-01-01T11:58:00Z")).toBe("2 minutes ago");
    expect(relativeTime("2026-01-01T09:00:00Z")).toBe("3 hours ago");
    expect(relativeTime("2025-12-30T12:00:00Z")).toBe("2 days ago");
  });

  it("collapses sub-second differences", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-01-01T12:00:00Z"));

    expect(relativeTime("2026-01-01T11:59:59.700Z")).toBe("just now");
  });

  it("renders a dash when there is no timestamp", () => {
    expect(relativeTime(null)).toBe("—");
  });
});

describe("formatJson", () => {
  it("pretty prints objects", () => {
    expect(formatJson({ a: 1 })).toBe('{\n  "a": 1\n}');
  });

  it("does not throw on circular structures", () => {
    const circular: Record<string, unknown> = {};
    circular.self = circular;

    expect(() => formatJson(circular)).not.toThrow();
  });
});

describe("pluralize", () => {
  it("uses the singular for exactly one", () => {
    expect(pluralize(1, "node")).toBe("1 node");
    expect(pluralize(0, "node")).toBe("0 nodes");
    expect(pluralize(3, "node")).toBe("3 nodes");
  });
});
