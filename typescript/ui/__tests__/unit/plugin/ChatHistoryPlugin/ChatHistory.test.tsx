import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, Mock } from "vitest";

vi.mock("../../../../src/core/stores/HistoryStore/useHistoryStore", () => {
  return {
    useHistoryStore: vi.fn(),
  };
});

vi.mock("../../../../src/core/stores/HistoryStore/selectors", () => {
  const selectConversationMock = vi.fn();
  const deleteConversationMock = vi.fn();
  const newConversationMock = vi.fn();
  return {
    useHistoryActions: () => ({
      selectConversation: selectConversationMock,
      deleteConversation: deleteConversationMock,
      newConversation: newConversationMock,
    }),
  };
});

import userEvent from "@testing-library/user-event";
import { useHistoryActions } from "../../../../src/core/stores/HistoryStore/selectors";
import { useHistoryStore } from "../../../../src/core/stores/HistoryStore/useHistoryStore";
import ChatHistory from "../../../../src/plugins/ChatHistoryPlugin/components/ChatHistory";
import { HistoryStore } from "../../../../src/types/history";
import { isTemporaryConversation } from "../../../../src/core/stores/HistoryStore/historyStore";

const MOCK_CONVERSATIONS: HistoryStore["conversations"] = {
  "mock-id-1": {
    history: {},
    followupMessages: null,
    serverState: null,
    conversationId: "mock-id-1",
    eventsLog: [],
    lastMessageId: null,
    chatOptions: undefined,
    isLoading: false,
    abortController: null,
  },
  "mock-id-2": {
    history: {},
    followupMessages: null,
    serverState: null,
    conversationId: "mock-id-2",
    eventsLog: [],
    lastMessageId: null,
    chatOptions: undefined,
    isLoading: false,
    abortController: null,
  },
  "temp-mock-id-1": {
    history: {},
    followupMessages: null,
    serverState: null,
    conversationId: "temp-mock-id-1",
    eventsLog: [],
    lastMessageId: null,
    chatOptions: undefined,
    isLoading: false,
    abortController: null,
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
        if (isTemporaryConversation(MOCK_CONVERSATIONS[key].conversationId)) {
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
        if (isTemporaryConversation(MOCK_CONVERSATIONS[key].conversationId)) {
          return;
        }

        console.log(`delete-conversation-${key}`);
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
    const newConversationMock = useHistoryActions().newConversation;
    expect(newConversationMock).toHaveBeenCalled();
  });
});
