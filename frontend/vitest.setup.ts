import "@testing-library/jest-dom/vitest";

// jsdom does not implement these, and both are used by @xyflow/react and by
// components that respond to container size.
globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
} as unknown as typeof ResizeObserver;

globalThis.DOMMatrixReadOnly ??= class {
  m22 = 1;
  constructor(_transform?: string) {}
} as unknown as typeof DOMMatrixReadOnly;

Object.defineProperty(globalThis, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});
