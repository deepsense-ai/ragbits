import { IconProps } from "@iconify/react";
import "@testing-library/jest-dom";
import { PropsWithChildren } from "react";
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

// Disable framer-motion animations so portals/modals render immediately
vi.mock("framer-motion", async () => {
  return {
    // No-op presence
    AnimatePresence: ({ children }: { children: React.ReactNode }) => (
      <>{children}</>
    ),
    // Render motion.* as simple divs
    motion: new Proxy(
      {},
      {
        get:
          () =>
          ({ children, ...props }: PropsWithChildren) => (
            <div {...props}>{children}</div>
          ),
      },
    ),
  };
});

Object.defineProperty(window, "scrollTo", {
  value: vi.fn(),
  writable: true,
});

afterEach(() => {
  vi.clearAllTimers();
  vi.useRealTimers();
});
