import "@testing-library/jest-dom";
import { vi } from "vitest";
Object.defineProperty(window, "scrollTo", {
  value: vi.fn(),
  writable: true,
});
