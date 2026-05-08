import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, Mock } from "vitest";
import ShareButton from "../../../../src/plugins/SharePlugin/components/ShareButton";
import { useHistoryStore } from "../../../../src/core/stores/HistoryStore/useHistoryStore";
import { useConversationProperty } from "../../../../src/core/stores/HistoryStore/selectors";

interface FakeEndpointCall {
  mock: Mock;
  data: unknown;
  error: Error | null;
  isLoading: boolean;
  reset: Mock;
  abort: Mock;
}

const endpointCalls: Record<string, FakeEndpointCall> = {};
const makeRequestMock = vi.fn();

function getEndpointCall(
  endpoint: string,
  method: string = "GET",
): FakeEndpointCall {
  const key = `${method} ${endpoint}`;
  if (!endpointCalls[key]) {
    endpointCalls[key] = {
      mock: vi.fn(),
      data: null,
      error: null,
      isLoading: false,
      reset: vi.fn(),
      abort: vi.fn(),
    };
  }
  return endpointCalls[key];
}

vi.mock("@ragbits/api-client-react", async () => {
  const actual = await vi.importActual("@ragbits/api-client-react");
  return {
    ...actual,
    useRagbitsCall: (endpoint: string, opts?: { method?: string }) => {
      const entry = getEndpointCall(endpoint, opts?.method ?? "GET");
      return {
        call: entry.mock,
        data: entry.data,
        error: entry.error,
        isLoading: entry.isLoading,
        reset: entry.reset,
        abort: entry.abort,
      };
    },
    useRagbitsContext: () => ({
      client: { makeRequest: makeRequestMock },
      config: null,
    }),
  };
});

vi.mock("../../../../src/core/stores/HistoryStore/useHistoryStore", () => ({
  useHistoryStore: vi.fn(),
}));

vi.mock("../../../../src/core/stores/HistoryStore/selectors", () => ({
  useConversationProperty: vi.fn(),
}));

function mockHistoryStore(conversationId: string = "conv-123") {
  (useHistoryStore as Mock).mockImplementation((selector) =>
    selector({ currentConversation: conversationId }),
  );
}

function mockConversationProperty(isShared: boolean = false) {
  (useConversationProperty as Mock).mockImplementation((selector) =>
    selector({ isShared }),
  );
}

describe("ShareButton", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    for (const key of Object.keys(endpointCalls)) {
      delete endpointCalls[key];
    }
    mockHistoryStore();
    mockConversationProperty(false);
    makeRequestMock.mockResolvedValue({
      conversation_id: "conv-123",
      messages: [],
      is_shared: false,
      shared_by: null,
      shares: [],
    });
    getEndpointCall(
      "/api/conversations/:conversationId/shares",
      "PUT",
    ).mock.mockResolvedValue([]);
    getEndpointCall(
      "/api/conversations/:conversationId/shares/:recipient",
      "DELETE",
    ).mock.mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: vi.fn() },
      configurable: true,
    });
  });

  it("opens and closes the share modal", async () => {
    const user = userEvent.setup();
    render(<ShareButton />);

    const trigger = screen.getByRole("button", { name: /share conversation/i });
    await user.click(trigger);

    expect(
      await screen.findByRole("textbox", { name: /recipient identifier/i }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /cancel/i }));
    await waitFor(() =>
      expect(
        screen.queryByRole("textbox", { name: /recipient identifier/i }),
      ).not.toBeInTheDocument(),
    );
  });

  it("adds a recipient and calls updateShares on save", async () => {
    const putMock = getEndpointCall(
      "/api/conversations/:conversationId/shares",
      "PUT",
    ).mock;
    putMock.mockResolvedValue([
      { recipient: "alice@example.com", shared_at: "2025-01-01T00:00:00Z" },
    ]);

    const user = userEvent.setup();
    render(<ShareButton />);

    await user.click(
      screen.getByRole("button", { name: /share conversation/i }),
    );

    const input = await screen.findByRole("textbox", {
      name: /recipient identifier/i,
    });
    await user.type(input, "alice@example.com{Enter}");

    await user.click(screen.getByRole("button", { name: /^share$/i }));

    await waitFor(() =>
      expect(putMock).toHaveBeenCalledWith({
        pathParams: { conversationId: "conv-123" },
        body: { recipients: ["alice@example.com"] },
      }),
    );
  });

  it("copies share link when clicking Copy link", async () => {
    const user = userEvent.setup();
    const writeTextSpy = vi.spyOn(navigator.clipboard, "writeText");
    render(<ShareButton />);

    await user.click(
      screen.getByRole("button", { name: /share conversation/i }),
    );
    await user.click(await screen.findByRole("button", { name: /copy link/i }));

    expect(writeTextSpy).toHaveBeenCalledTimes(1);
    expect(writeTextSpy.mock.calls[0][0]).toContain("/conversation/conv-123");
  });

  it("loads existing shares and allows revoking them", async () => {
    makeRequestMock.mockResolvedValue({
      conversation_id: "conv-123",
      messages: [],
      is_shared: false,
      shared_by: null,
      shares: [
        { recipient: "bob@example.com", shared_at: "2025-01-01T00:00:00Z" },
      ],
    });
    const deleteMock = getEndpointCall(
      "/api/conversations/:conversationId/shares/:recipient",
      "DELETE",
    ).mock;

    const user = userEvent.setup();
    render(<ShareButton />);

    await user.click(
      screen.getByRole("button", { name: /share conversation/i }),
    );

    const removeBtn = await screen.findByRole("button", {
      name: /remove bob@example\.com/i,
    });
    await user.click(removeBtn);

    await waitFor(() =>
      expect(deleteMock).toHaveBeenCalledWith({
        pathParams: {
          conversationId: "conv-123",
          recipient: "bob@example.com",
        },
      }),
    );
  });

  it("renders nothing when conversation is already shared", () => {
    mockConversationProperty(true);
    const { container } = render(<ShareButton />);
    expect(container.firstChild).toBeNull();
  });
});
