import { describe, expect, it } from "vitest";
import { handleError } from "../../src/core/stores/HistoryStore/eventHandlers/messageHandlers";
import { ChatMessage, Conversation } from "../../src/types/history";
import { ErrorChatResponse, MessageRole } from "@ragbits/api-client";

describe("handleError", () => {
  const createMockMessage = (): ChatMessage => ({
    id: "test-message",
    role: MessageRole.Assistant,
    content: "",
  });

  const createMockConversation = (message: ChatMessage): Conversation => ({
    history: { [message.id]: message },
    followupMessages: null,
    serverState: null,
    conversationId: "test-conversation",
    eventsLog: [],
    lastMessageId: message.id,
    chatOptions: undefined,
    isLoading: false,
    abortController: null,
  });

  const createMockContext = (messageId: string) => ({
    conversationIdRef: { current: "test-conversation" },
    messageId,
  });

  it("sets error message on the message", () => {
    const message = createMockMessage();
    const draft = createMockConversation(message);
    const response: ErrorChatResponse = {
      type: "error",
      content: { message: "An error occurred" },
    };
    const ctx = createMockContext(message.id);

    handleError(response, draft, ctx);

    expect(draft.history[message.id].error).toBe("An error occurred");
  });

  it("overwrites existing error with new error", () => {
    const message = createMockMessage();
    message.error = "Previous error";
    const draft = createMockConversation(message);

    const response: ErrorChatResponse = {
      type: "error",
      content: { message: "New error" },
    };
    const ctx = createMockContext(message.id);

    handleError(response, draft, ctx);

    expect(draft.history[message.id].error).toBe("New error");
  });

  it("handles empty error message", () => {
    const message = createMockMessage();
    const draft = createMockConversation(message);
    const response: ErrorChatResponse = {
      type: "error",
      content: { message: "" },
    };
    const ctx = createMockContext(message.id);

    handleError(response, draft, ctx);

    expect(draft.history[message.id].error).toBe("");
  });
});
