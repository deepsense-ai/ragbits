import { IconProps } from "@iconify/react";
import "@testing-library/jest-dom";
import { afterEach, vi } from "vitest";

vi.mock("react-router", () => ({
  useNavigate: () => vi.fn(),
}));

vi.mock("@iconify/react", () => ({
  // ref is not a part of IconProps so it cannot be done like { icon, ...props }
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
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
