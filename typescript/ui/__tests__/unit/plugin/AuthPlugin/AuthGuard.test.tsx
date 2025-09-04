import { describe, it, beforeEach, vi, expect, Mock } from "vitest";
import { render, screen } from "@testing-library/react";
import { useStore } from "zustand";
import AuthGuard from "../../../../src/plugins/AuthPlugin/components/AuthGuard";

// --- mocks ---
vi.mock("zustand", async (importOriginal) => ({
  ...(await importOriginal()),
  useStore: vi.fn(),
}));

vi.mock("../../../../src/plugins/AuthPlugin/stores/authStore", () => ({
  authStore: {},
}));

vi.mock(
  "../../../../src/plugins/AuthPlugin/contexts/AuthStoreContext/AuthStoreContextProvider",
  () => ({
    AuthStoreContextProvider: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="auth-store-context">{children}</div>
    ),
  }),
);

vi.mock("../../../../src/plugins/AuthPlugin/components/AuthWatcher", () => ({
  AuthWatcher: () => <div data-testid="auth-watcher" />,
}));

let mockPathname = "/";
vi.mock("react-router", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router")>();
  return {
    ...actual,
    useLocation: () => ({ pathname: mockPathname }),
    Navigate: ({ to, replace }: { to: string; replace?: boolean }) => (
      <div
        data-testid="navigate"
        data-to={to}
        data-replace={replace?.toString()}
      />
    ),
  };
});

describe("AuthGuard", () => {
  const useStoreMock = useStore as Mock;

  beforeEach(() => {
    vi.resetAllMocks();
    mockPathname = "/"; // default
  });

  it("renders children if route is /login regardless of auth state", () => {
    mockPathname = "/login";
    useStoreMock.mockReturnValue(false);

    render(
      <AuthGuard>
        <div data-testid="child">Login page child</div>
      </AuthGuard>,
    );

    expect(screen.getByTestId("child")).toBeInTheDocument();
    expect(screen.queryByTestId("auth-watcher")).not.toBeInTheDocument();
    expect(screen.queryByTestId("navigate")).not.toBeInTheDocument();
  });

  it("wraps children and renders AuthWatcher if authenticated", () => {
    mockPathname = "/dashboard";
    useStoreMock.mockReturnValue(true);

    render(
      <AuthGuard>
        <div data-testid="child">Dashboard child</div>
      </AuthGuard>,
    );

    expect(screen.getByTestId("child")).toBeInTheDocument();
    expect(screen.getByTestId("auth-store-context")).toBeInTheDocument();
    expect(screen.getByTestId("auth-watcher")).toBeInTheDocument();
    expect(screen.queryByTestId("navigate")).not.toBeInTheDocument();
  });

  it("renders Navigate to /login if not authenticated", () => {
    mockPathname = "/dashboard";
    useStoreMock.mockReturnValue(false);

    render(
      <AuthGuard>
        <div data-testid="child">Dashboard child</div>
      </AuthGuard>,
    );

    const nav = screen.getByTestId("navigate");
    expect(nav).toHaveAttribute("data-to", "/login");
    expect(nav).toHaveAttribute("data-replace", "true");
    expect(screen.queryByTestId("child")).not.toBeInTheDocument();
  });
});
