import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, Mock } from "vitest";

vi.mock("../../src/core/stores/historyStore", async (importOriginal) => {
  const selectConversationMock = vi.fn();
  const deleteConversationMock = vi.fn();
  const clearHistoryMock = vi.fn();
  const stopAnsweringMock = vi.fn();
  const actual =
    await importOriginal<typeof import("../../src/core/stores/historyStore")>();
  return {
    getConversationKey: actual.getConversationKey,
    useHistoryStore: vi.fn(),
    useHistoryActions: () => ({
      selectConversation: selectConversationMock,
      deleteConversation: deleteConversationMock,
      clearHistory: clearHistoryMock,
      stopAnswering: stopAnsweringMock,
    }),
  };
});

import {
  getConversationKey,
  useHistoryActions,
  useHistoryStore,
} from "../../src/core/stores/historyStore";
import userEvent from "@testing-library/user-event";
import ChatHistory from "../../src/core/components/ChatHistory";
import { HistoryStore } from "../../src/types/history";

const MOCK_CONVERSATIONS: HistoryStore["conversations"] = {
  "mock-id-1": {
    history: {},
    followupMessages: null,
    serverState: null,
    conversationId: "mock-id-1",
    eventsLog: [],
    lastMessageId: null,
    chatOptions: undefined,
  },
  "mock-id-2": {
    history: {},
    followupMessages: null,
    serverState: null,
    conversationId: "mock-id-2",
    eventsLog: [],
    lastMessageId: null,
    chatOptions: undefined,
  },
  null: {
    history: {},
    followupMessages: null,
    serverState: null,
    conversationId: "null",
    eventsLog: [],
    lastMessageId: null,
    chatOptions: undefined,
  },
};

function mockStore(currentConversation: string | null) {
  (useHistoryStore as unknown as Mock).mockImplementation((selector) =>
    selector({
      currentConversation,
      conversations: MOCK_CONVERSATIONS,
    }),
  );
}

describe("ChatHistory", () => {
  describe("renders correctly", () => {
    it("renders all conversations", () => {
      const mockConversationsKeys = Object.keys(MOCK_CONVERSATIONS);
      mockStore(null);
      render(<ChatHistory />);

      mockConversationsKeys.forEach((key) => {
        if (key === getConversationKey(null)) {
          return;
        }

        expect(screen.getByTitle(key)).toBeInTheDocument();
      });
    });

    it("renders active conversation", () => {
      const mockConversationsKeys = Object.keys(MOCK_CONVERSATIONS);
      const selectedKey = mockConversationsKeys[0];
      mockStore(selectedKey);
      render(<ChatHistory />);

      const selectedConversation = screen.getByTitle(selectedKey);
      expect(selectedConversation).toHaveAttribute("data-active", "true");
    });

    it("renders delete buttons", () => {
      const mockConversationsKeys = Object.keys(MOCK_CONVERSATIONS);
      mockStore(null);
      render(<ChatHistory />);

      mockConversationsKeys.forEach((key) => {
        if (key === getConversationKey(null)) {
          return;
        }

        expect(
          screen.getByTestId(`delete-conversation-${key}`),
        ).toBeInTheDocument();
      });
    });
  });

  it("calls `selectConversation`", async () => {
    const selectedKey = Object.keys(MOCK_CONVERSATIONS)[0];
    mockStore(null);
    render(<ChatHistory />);

    const selectButton = screen.getByTestId(
      `select-conversation-${selectedKey}`,
    );
    expect(selectButton).toBeInTheDocument();
    const user = userEvent.setup();
    await user.click(selectButton);

    const selectMock = useHistoryActions().selectConversation;
    expect(selectMock).toHaveBeenCalledWith(selectedKey);
  });

  it("calls `deleteConversation`", async () => {
    const selectedKey = Object.keys(MOCK_CONVERSATIONS)[0];
    mockStore(null);
    render(<ChatHistory />);

    const deleteButton = screen.getByTestId(
      `delete-conversation-${selectedKey}`,
    );
    expect(deleteButton).toBeInTheDocument();
    const user = userEvent.setup();
    await user.click(deleteButton);

    const deleteMock = useHistoryActions().deleteConversation;
    expect(deleteMock).toHaveBeenCalledWith(selectedKey);
  });

  it('calls clearHistory and stopAnswering when "clear chat" button is clicked', async () => {
    mockStore(null);
    render(<ChatHistory />);
    const user = userEvent.setup();
    const clearChatButton = screen.getByTestId(
      "chat-history-clear-chat-button",
    );
    await user.click(clearChatButton);
    const clearHistoryMock = useHistoryActions().clearHistory;
    const stopAnsweringMock = useHistoryActions().stopAnswering;
    expect(clearHistoryMock).toHaveBeenCalled();
    expect(stopAnsweringMock).toHaveBeenCalled();
  });
});
