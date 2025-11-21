import { useRagbitsCall } from "@ragbits/api-client-react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useNavigate } from "react-router";
import { describe, it, vi, beforeEach, expect, Mock, afterEach } from "vitest";
import { useStore } from "zustand";
import { useInitializeUserStore } from "../../../../src/core/stores/HistoryStore/useInitializeUserStore";
import CredentialsLogin from "../../../../src/plugins/AuthPlugin/components/CredentialsLogin";

vi.mock("@ragbits/api-client-react", () => ({
  useRagbitsCall: vi.fn(() => ({
    call: vi.fn(),
    isLoading: false,
    error: null,
  })),
}));

vi.mock("zustand", async (importOriginal) => ({
  ...(await importOriginal()),
  useStore: vi.fn(),
}));

vi.mock("react-router", () => ({
  useNavigate: vi.fn(),
}));

vi.mock(
  "../../../../src/core/stores/HistoryStore/useInitializeUserStore",
  () => ({
    useInitializeUserStore: vi.fn(),
  }),
);

describe("CredentialsLogin component", () => {
  const user = userEvent.setup();
  let loginMock: Mock;
  let navigateMock: Mock;
  let initializeUserStoreMock: Mock;
  let callMock: Mock;

  beforeEach(() => {
    loginMock = vi.fn();
    navigateMock = vi.fn();
    initializeUserStoreMock = vi.fn();
    callMock = vi.fn();

    (useStore as Mock).mockImplementation(
      (_: unknown, selector: (...args: unknown[]) => unknown) =>
        selector({ login: loginMock }),
    );
    (useRagbitsCall as Mock).mockReturnValue({ call: callMock });
    (useNavigate as Mock).mockReturnValue(navigateMock);
    (useInitializeUserStore as Mock).mockReturnValue(initializeUserStoreMock);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders username and password inputs and submit button", () => {
    render(<CredentialsLogin />);
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /sign in/i }),
    ).toBeInTheDocument();
  });

  it("updates input values when typing", async () => {
    render(<CredentialsLogin />);
    const usernameInput = screen.getByLabelText(/username/i);
    const passwordInput = screen.getByLabelText(/password/i);

    await user.type(usernameInput, "user123");
    await user.type(passwordInput, "password");

    expect(usernameInput).toHaveValue("user123");
    expect(passwordInput).toHaveValue("password");
  });

  it("successful login calls API, login, initialize store, and navigates", async () => {
    callMock.mockResolvedValue({
      success: true,
      user: { user_id: "user-1" },
    });

    render(<CredentialsLogin />);
    const usernameInput = screen.getByLabelText(/username/i);
    const passwordInput = screen.getByLabelText(/password/i);

    await user.type(usernameInput, "user123");
    await user.type(passwordInput, "password");

    const submitBtn = screen.getByRole("button", { name: /sign in/i });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(callMock).toHaveBeenCalledWith({
        body: { username: "user123", password: "password" },
      });
      expect(loginMock).toHaveBeenCalledWith({ user_id: "user-1" });
      expect(initializeUserStoreMock).toHaveBeenCalledWith("user-1");
      expect(navigateMock).toHaveBeenCalledWith("/");
    });
  });

  it("failed login sets error", async () => {
    callMock.mockResolvedValue({ success: false });

    render(<CredentialsLogin />);
    const usernameInput = screen.getByLabelText(/username/i);
    const passwordInput = screen.getByLabelText(/password/i);

    await user.type(usernameInput, "user123");
    await user.type(passwordInput, "password");

    const submitBtn = screen.getByRole("button", { name: /sign in/i });
    await user.click(submitBtn);

    await waitFor(async () => {
      expect(callMock).toHaveBeenCalled();
      expect(loginMock).not.toHaveBeenCalled();
      expect(initializeUserStoreMock).not.toHaveBeenCalled();
      expect(navigateMock).not.toHaveBeenCalled();
      expect(
        await screen.findByText(/we couldn't sign you in/i),
      ).toBeInTheDocument();
    });
  });

  it("handles API errors gracefully", async () => {
    callMock.mockRejectedValue(new Error("Network error"));

    render(<CredentialsLogin />);
    const usernameInput = screen.getByLabelText(/username/i);
    const passwordInput = screen.getByLabelText(/password/i);

    await user.type(usernameInput, "user123");
    await user.type(passwordInput, "password");

    const submitBtn = screen.getByRole("button", { name: /sign in/i });
    await user.click(submitBtn);

    await waitFor(async () => {
      expect(loginMock).not.toHaveBeenCalled();
      expect(initializeUserStoreMock).not.toHaveBeenCalled();
      expect(navigateMock).not.toHaveBeenCalled();
      expect(
        await screen.findByText(/we couldn't sign you in/i),
      ).toBeInTheDocument();
    });
  });
});
