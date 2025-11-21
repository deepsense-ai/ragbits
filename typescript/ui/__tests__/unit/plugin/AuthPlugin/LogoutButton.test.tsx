import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, vi, beforeEach, expect, Mock, afterEach } from "vitest";
import LogoutButton from "../../../../src/plugins/AuthPlugin/components/LogoutButton";
import { useRagbitsCall } from "@ragbits/api-client-react";
import { useStore } from "zustand";
import { useNavigate } from "react-router";

vi.mock("@ragbits/api-client-react", () => ({
  useRagbitsCall: vi.fn(() => ({
    call: vi.fn(),
  })),
}));

vi.mock("zustand", async (importOriginal) => ({
  ...(await importOriginal()),
  useStore: vi.fn(),
}));

vi.mock("react-router", () => ({
  useNavigate: vi.fn(),
}));

describe("LogoutButton", () => {
  const user = userEvent.setup();
  let callMock: Mock;
  let logoutMock: Mock;
  let navigateMock: Mock;

  beforeEach(async () => {
    callMock = vi.fn().mockResolvedValue({ success: true });
    logoutMock = vi.fn();
    navigateMock = vi.fn();

    (useRagbitsCall as Mock).mockReturnValue({ call: callMock });
    (useStore as Mock).mockImplementation(
      (_: unknown, selector: (...args: unknown[]) => unknown) =>
        selector({ logout: logoutMock, isAuthenticated: true }),
    );
    (useNavigate as Mock).mockReturnValue(navigateMock);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders logout button", () => {
    render(<LogoutButton />);
    const button = screen.getByTestId("logout-button");
    expect(button).toBeInTheDocument();
    expect(screen.getByLabelText("Logout")).toBeInTheDocument();
  });

  it("calls API, logout, and navigates when authenticated", async () => {
    render(<LogoutButton />);
    const button = screen.getByTestId("logout-button");

    await user.click(button);

    await waitFor(() => {
      expect(callMock).toHaveBeenCalledWith();
      expect(logoutMock).toHaveBeenCalled();
      expect(navigateMock).toHaveBeenCalledWith("/login");
    });
  });

  it("navigates directly when not authenticated", async () => {
    (useStore as Mock).mockImplementation(
      (_: unknown, selector: (...args: unknown[]) => unknown) =>
        selector({ logout: logoutMock, isAuthenticated: false }),
    );

    render(<LogoutButton />);
    const button = screen.getByTestId("logout-button");
    await user.click(button);

    await waitFor(() => {
      expect(callMock).not.toHaveBeenCalled();
      expect(logoutMock).not.toHaveBeenCalled();
      expect(navigateMock).toHaveBeenCalledWith("/login");
    });
  });

  it("does not logout locally if API returns success=false", async () => {
    callMock.mockResolvedValueOnce({ success: false });
    render(<LogoutButton />);
    const button = screen.getByTestId("logout-button");
    await user.click(button);

    await waitFor(() => {
      expect(callMock).toHaveBeenCalled();
    });

    // Wait a bit more to ensure logout/navigate are not called
    await new Promise((resolve) => setTimeout(resolve, 100));
    expect(logoutMock).not.toHaveBeenCalled();
    expect(navigateMock).not.toHaveBeenCalled();
  });

  it("does not logout locally if API fails", async () => {
    callMock.mockRejectedValueOnce(new Error("API failed"));
    render(<LogoutButton />);
    const button = screen.getByTestId("logout-button");
    await user.click(button);

    await waitFor(() => {
      expect(callMock).toHaveBeenCalled();
    });

    // Wait a bit more to ensure logout/navigate are not called
    await new Promise((resolve) => setTimeout(resolve, 100));
    expect(logoutMock).not.toHaveBeenCalled();
    expect(navigateMock).not.toHaveBeenCalled();
  });
});
