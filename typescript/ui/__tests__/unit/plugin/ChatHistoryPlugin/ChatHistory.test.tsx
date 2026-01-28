import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, Mock } from "vitest";

vi.mock("../../../../src/core/stores/HistoryStore/useHistoryStore", () => {
  return {
    useHistoryStore: vi.fn(),
  };
});

const selectConversationMock = vi.fn();
const deleteConversationMock = vi.fn();
const newConversationMock = vi.fn();
const setConversationPropertiesMock = vi.fn();

vi.mock("../../../../src/core/stores/HistoryStore/selectors", () => {
  return {
    useHistoryActions: () => ({
      selectConversation: selectConversationMock,
      deleteConversation: deleteConversationMock,
      newConversation: newConversationMock,
      setConversationProperties: setConversationPropertiesMock,
    }),
  };
});

import userEvent from "@testing-library/user-event";
import { useHistoryActions } from "../../../../src/core/stores/HistoryStore/selectors";
import { useHistoryStore } from "../../../../src/core/stores/HistoryStore/useHistoryStore";
import ChatHistory from "../../../../src/plugins/ChatHistoryPlugin/components/ChatHistory";
import { HistoryStore } from "../../../../src/core/types/history";
import { isTemporaryConversation } from "../../../../src/core/stores/HistoryStore/utils";

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

    it("renders dropdown buttons", () => {
      const mockConversationsKeys = Object.keys(MOCK_CONVERSATIONS);
      mockStore(null);
      render(<ChatHistory />);

      mockConversationsKeys.forEach((key) => {
        if (isTemporaryConversation(MOCK_CONVERSATIONS[key].conversationId)) {
          return;
        }

        expect(
          screen.getByTestId(`dropdown-conversation-${key}`),
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
    const user = userEvent.setup();

    const dropdownButton = screen.getByTestId(
      `dropdown-conversation-${selectedKey}`,
    );
    await user.click(dropdownButton);
    const deleteButton = screen.getByTestId(
      `delete-conversation-${selectedKey}`,
    );
    expect(deleteButton).toBeInTheDocument();
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

  it("starts editing when Edit is clicked (input appears and is focused)", async () => {
    mockStore(null);
    render(<ChatHistory />);

    const key = Object.keys(MOCK_CONVERSATIONS)[0];
    const user = userEvent.setup();

    const dropdownButton = screen.getByTestId(`dropdown-conversation-${key}`);
    await user.click(dropdownButton);

    const editButton = screen.getByTestId(`edit-conversation-${key}`);
    await user.click(editButton);

    const input = await screen.findByDisplayValue(
      MOCK_CONVERSATIONS[key].conversationId,
    );
    expect(input).toBeInTheDocument();

    await waitFor(() => {
      expect(document.activeElement).toBe(input);
    });
  });

  it("saves edited value on Enter and calls setConversationProperties", async () => {
    mockStore(null);
    render(<ChatHistory />);

    const key = Object.keys(MOCK_CONVERSATIONS)[0];
    const user = userEvent.setup();

    const dropdownButton = screen.getByTestId(`dropdown-conversation-${key}`);
    await user.click(dropdownButton);

    const editButton = screen.getByTestId(`edit-conversation-${key}`);
    await user.click(editButton);

    const input = await screen.findByDisplayValue(
      MOCK_CONVERSATIONS[key].conversationId,
    );
    expect(input).toBeInTheDocument();

    await waitFor(() => {
      expect(document.activeElement).toBe(input);
    });
  });

  it("does NOT call setConversationProperties for whitespace-only input", async () => {
    mockStore(null);
    render(<ChatHistory />);

    const key = Object.keys(MOCK_CONVERSATIONS)[0];
    const user = userEvent.setup();

    await user.click(screen.getByTestId(`dropdown-conversation-${key}`));
    await user.click(screen.getByTestId(`edit-conversation-${key}`));

    const input = await screen.findByDisplayValue(
      MOCK_CONVERSATIONS[key].conversationId,
    );

    await user.clear(input);
    await user.type(input, "   ");
    await user.keyboard("{Enter}");

    await waitFor(() => {
      expect(setConversationPropertiesMock).not.toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(
        screen.queryByDisplayValue(MOCK_CONVERSATIONS[key].conversationId),
      ).not.toBeInTheDocument();
    });
  });

  it("cancels edit when Escape is pressed and does not call setConversationProperties", async () => {
    mockStore(null);
    render(<ChatHistory />);

    const key = Object.keys(MOCK_CONVERSATIONS)[0];
    const user = userEvent.setup();

    await user.click(screen.getByTestId(`dropdown-conversation-${key}`));
    await user.click(screen.getByTestId(`edit-conversation-${key}`));

    const input = await screen.findByDisplayValue(
      MOCK_CONVERSATIONS[key].conversationId,
    );

    await user.type(input, "temp");
    await user.type(input, "{Escape}");

    await waitFor(() => {
      expect(setConversationPropertiesMock).not.toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.queryByDisplayValue("temp")).not.toBeInTheDocument();
    });
  });
});
