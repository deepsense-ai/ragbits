import { describe, it, vi, beforeEach, afterEach, expect, Mock } from "vitest";
import { useStore } from "zustand";
import { AuthWatcher } from "../../../../src/plugins/AuthPlugin/components/AuthWatcher";
import { render, waitFor } from "@testing-library/react";
import { useRagbitsContext } from "@ragbits/api-client-react";

vi.mock("zustand", async (importOriginal) => ({
  ...(await importOriginal()),
  useStore: vi.fn(),
}));

vi.mock(
  "../../../../src/core/stores/HistoryStore/useInitializeUserStore",
  () => ({
    useInitializeUserStore: vi.fn(() => vi.fn()),
  }),
);

vi.mock("@ragbits/api-client-react", () => ({
  useRagbitsContext: vi.fn(),
}));

describe("AuthWatcher", () => {
  let loginMock: Mock;
  let logoutMock: Mock;
  let setHydratedMock: Mock;
  let useStoreMock: Mock;
  let mockMakeRequest: Mock;

  beforeEach(() => {
    loginMock = vi.fn();
    logoutMock = vi.fn();
    setHydratedMock = vi.fn();
    mockMakeRequest = vi.fn();
    useStoreMock = useStore as Mock;

    useStoreMock.mockReturnValue({
      login: loginMock,
      logout: logoutMock,
      setHydrated: setHydratedMock,
    });

    (useRagbitsContext as Mock).mockReturnValue({
      client: {
        makeRequest: mockMakeRequest,
      },
    });
  });

  afterEach(() => {
    vi.resetAllMocks();
    vi.clearAllMocks();
  });

  it("logs in user when /api/user returns valid user", async () => {
    const mockUser = {
      user_id: "user-123",
      username: "testuser",
      email: "test@example.com",
    };
    mockMakeRequest.mockResolvedValue(mockUser);

    render(<AuthWatcher />);

    await waitFor(() => {
      expect(mockMakeRequest).toHaveBeenCalledWith("/api/user");
      expect(loginMock).toHaveBeenCalledWith(mockUser);
      expect(logoutMock).not.toHaveBeenCalled();
      expect(setHydratedMock).toHaveBeenCalled();
    });
  });

  it("logs out user when /api/user returns null", async () => {
    mockMakeRequest.mockResolvedValue(null);

    render(<AuthWatcher />);

    await waitFor(() => {
      expect(mockMakeRequest).toHaveBeenCalledWith("/api/user");
      expect(logoutMock).toHaveBeenCalled();
      expect(loginMock).not.toHaveBeenCalled();
      expect(setHydratedMock).toHaveBeenCalled();
    });
  });

  it("logs out user when /api/user throws error", async () => {
    mockMakeRequest.mockRejectedValue(new Error("Unauthorized"));

    render(<AuthWatcher />);

    await waitFor(() => {
      expect(mockMakeRequest).toHaveBeenCalledWith("/api/user");
      expect(logoutMock).toHaveBeenCalled();
      expect(loginMock).not.toHaveBeenCalled();
      expect(setHydratedMock).toHaveBeenCalled();
    });
  });

  it("renders nothing (returns null)", () => {
    mockMakeRequest.mockResolvedValue(null);

    const { container } = render(<AuthWatcher />);

    expect(container.firstChild).toBeNull();
  });
});
