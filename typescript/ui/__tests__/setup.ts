import "@testing-library/jest-dom";
import { afterEach, vi } from "vitest";
Object.defineProperty(window, "scrollTo", {
  value: vi.fn(),
  writable: true,
});

afterEach(() => {
  vi.clearAllTimers();
  vi.useRealTimers();
});
