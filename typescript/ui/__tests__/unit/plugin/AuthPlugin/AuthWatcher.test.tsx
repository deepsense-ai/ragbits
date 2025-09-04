import { useNavigate } from "react-router";
import { describe, it, vi, beforeEach, afterEach, expect, Mock } from "vitest";
import { useStore } from "zustand";
import { useConversationProperty } from "../../../../src/core/stores/HistoryStore/selectors";
import { AuthWatcher } from "../../../../src/plugins/AuthPlugin/components/AuthWatcher";
import { act, useState } from "react";
import { fireEvent, render, screen } from "@testing-library/react";

vi.mock("zustand", async (importOriginal) => ({
  ...(await importOriginal()),
  useStore: vi.fn(),
}));

vi.mock("../../../../src/core/stores/HistoryStore/selectors", () => ({
  useConversationProperty: vi.fn(),
}));

vi.mock("react-router", () => ({
  useNavigate: vi.fn(),
}));

describe("AuthWatcher", () => {
  let logoutMock: Mock;
  let navigateMock: Mock;
  let useStoreMock: Mock;
  let useConversationPropertyMock: Mock;

  beforeEach(() => {
    vi.useFakeTimers();
    logoutMock = vi.fn();
    navigateMock = vi.fn();
    useStoreMock = useStore as Mock;
    useConversationPropertyMock = useConversationProperty as Mock;

    useStoreMock.mockReturnValue({
      token: "token-123",
      tokenExpiration: Date.now() + 1000, // 1 second in the future
      logout: logoutMock,
    });
    useConversationPropertyMock.mockReturnValue(false);

    (useNavigate as Mock).mockReturnValue(navigateMock);
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.resetAllMocks();
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it("does nothing if token is null", () => {
    useStoreMock.mockReturnValue({
      token: null,
      tokenExpiration: null,
      logout: logoutMock,
    });

    render(<AuthWatcher />);
    vi.advanceTimersByTime(10000);
    expect(logoutMock).not.toHaveBeenCalled();
    expect(navigateMock).not.toHaveBeenCalled();
  });

  it("logs out immediately if token has expired", () => {
    const now = Date.now();
    useStoreMock.mockReturnValue({
      token: "token-123",
      tokenExpiration: now - 1000, // expired
      logout: logoutMock,
    });
    useConversationPropertyMock.mockReturnValue(false);

    render(<AuthWatcher />);
    vi.runAllTimers();

    expect(logoutMock).toHaveBeenCalled();
    expect(navigateMock).toHaveBeenCalledWith("/login");
  });

  it("waits for token expiration and then logs out", () => {
    const now = Date.now();
    useStoreMock.mockReturnValue({
      token: "token-123",
      tokenExpiration: now + 5000, // expires in 5s
      logout: logoutMock,
    });
    useConversationPropertyMock.mockReturnValue(false);

    render(<AuthWatcher />);
    vi.advanceTimersByTime(4999);
    expect(logoutMock).not.toHaveBeenCalled();

    vi.advanceTimersByTime(2); // pass expiration
    expect(logoutMock).toHaveBeenCalled();
    expect(navigateMock).toHaveBeenCalledWith("/login");
  });

  it("waits until conversations finish loading before logging out", async () => {
    const now = Date.now();
    useStoreMock.mockReturnValue({
      token: "token-123",
      tokenExpiration: now - 1000,
      logout: logoutMock,
    });

    const TestWrapper = () => {
      const [loading, setLoading] = useState(true);
      useConversationPropertyMock.mockReturnValue(loading);

      return (
        <>
          <AuthWatcher />
          <button
            onClick={() => {
              setLoading(false);
            }}
          >
            finish loading
          </button>
        </>
      );
    };

    render(<TestWrapper />);
    act(() => {
      vi.advanceTimersByTime(500);
    });
    expect(logoutMock).not.toHaveBeenCalled();

    fireEvent.click(screen.getByText("finish loading"));
    act(() => {
      vi.advanceTimersByTime(500);
    });

    expect(logoutMock).toHaveBeenCalledTimes(1);
    expect(navigateMock).toHaveBeenCalledWith("/login");
  });
});
