import { IconProps } from "@iconify/react";
import "@testing-library/jest-dom";
import { afterEach, vi } from "vitest";

vi.mock("@iconify/react", () => ({
  Icon: ({ icon, ref, ...props }: IconProps) => (
    <svg {...props}>{icon.toString()}</svg>
  ),
}));

Object.defineProperty(window, "scrollTo", {
  value: vi.fn(),
  writable: true,
});

afterEach(() => {
  vi.clearAllTimers();
  vi.useRealTimers();
});
