import { describe, it, vi, beforeEach, afterEach, expect, Mock } from "vitest";
import { useStore } from "zustand";
import { AuthWatcher } from "../../../../src/plugins/AuthPlugin/components/AuthWatcher";
import { render, waitFor } from "@testing-library/react";
import { useRagbitsCall } from "@ragbits/api-client-react";

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
  useRagbitsCall: vi.fn(),
}));

vi.mock("react-router", () => ({
  useNavigate: vi.fn(() => vi.fn()),
  useLocation: vi.fn(() => ({ pathname: "/" })),
}));

describe("AuthWatcher", () => {
  let loginMock: Mock;
  let logoutMock: Mock;
  let setHydratedMock: Mock;
  let useStoreMock: Mock;
  let mockCall: Mock;

  beforeEach(() => {
    loginMock = vi.fn();
    logoutMock = vi.fn();
    setHydratedMock = vi.fn();
    mockCall = vi.fn();
    useStoreMock = useStore as Mock;

    useStoreMock.mockReturnValue({
      login: loginMock,
      logout: logoutMock,
      setHydrated: setHydratedMock,
    });

    (useRagbitsCall as Mock).mockReturnValue({
      call: mockCall,
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
    mockCall.mockResolvedValue(mockUser);

    render(<AuthWatcher />);

    await waitFor(() => {
      expect(mockCall).toHaveBeenCalled();
      expect(loginMock).toHaveBeenCalledWith(mockUser);
      expect(logoutMock).not.toHaveBeenCalled();
      expect(setHydratedMock).toHaveBeenCalled();
    });
  });

  it("logs out user when /api/user returns null", async () => {
    mockCall.mockResolvedValue(null);

    render(<AuthWatcher />);

    await waitFor(() => {
      expect(mockCall).toHaveBeenCalled();
      expect(logoutMock).toHaveBeenCalled();
      expect(loginMock).not.toHaveBeenCalled();
      expect(setHydratedMock).toHaveBeenCalled();
    });
  });

  it("logs out user when /api/user throws error", async () => {
    mockCall.mockRejectedValue(new Error("Unauthorized"));

    render(<AuthWatcher />);

    await waitFor(() => {
      expect(mockCall).toHaveBeenCalled();
      expect(logoutMock).toHaveBeenCalled();
      expect(loginMock).not.toHaveBeenCalled();
      expect(setHydratedMock).toHaveBeenCalled();
    });
  });

  it("renders nothing (returns null)", () => {
    mockCall.mockResolvedValue(null);

    const { container } = render(<AuthWatcher />);

    expect(container.firstChild).toBeNull();
  });
});
