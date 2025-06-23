import { PropsWithChildren, useCallback, useMemo, useState } from "react";
import { HistoryContext } from "./HistoryContext.ts";
import { v4 as uuidv4 } from "uuid";
import {
  TypedChatResponse as ChatResponse,
  ChatResponseType,
  MessageRole,
  ServerState,
  useRagbitsStream,
  ChatRequest,
} from "ragbits-api-client-react";
import { ChatMessage, HistoryState } from "../../types/history.ts";
import { mapHistoryToMessages } from "../../core/utils/messageMapper";
import { noop } from "lodash";

export function HistoryProvider({ children }: PropsWithChildren) {
  const [history, setHistory] = useState<HistoryState>(new Map());
  const [serverState, setServerState] = useState<ServerState | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const chatFactory = useRagbitsStream("/api/chat");

  const updateHistoryState = (
    updater: (prev: HistoryState) => HistoryState,
  ) => {
    setHistory((prev) => updater(prev));
  };

  const addMessage = useCallback((message: Omit<ChatMessage, "id">): string => {
    const id = uuidv4();
    const newMessage: ChatMessage = { ...message, id };
    updateHistoryState((prev) => {
      const next = new Map(prev);
      next.set(id, newMessage);
      return next;
    });
    return id;
  }, []);

  const deleteMessage = useCallback((messageId: string): void => {
    updateHistoryState((prev) => {
      const next = new Map(prev);
      next.delete(messageId);
      return next;
    });
  }, []);

  const clearHistory = useCallback((): void => {
    setHistory(new Map());
    setServerState(null);
    setConversationId(null);
  }, []);

  const _handleNonHistoryResponse = useCallback(
    (response: ChatResponse): void => {
      switch (response.type) {
        case ChatResponseType.STATE_UPDATE:
          setServerState(response.content);
          break;
        case ChatResponseType.CONVERSATION_ID:
          setConversationId(response.content);
          break;
      }
    },
    [],
  );

  const _handleHistoryResponse = useCallback(
    (response: ChatResponse, messageId: string): void => {
      updateHistoryState((prev) => {
        const next = new Map(prev);
        const existingMessage = next.get(messageId);
        if (!existingMessage) {
          throw new Error(`Message ID ${messageId} not found in history`);
        }

        const updatedMessage = { ...existingMessage };
        switch (response.type) {
          case ChatResponseType.TEXT:
            updatedMessage.content += response.content;
            break;
          case ChatResponseType.REFERENCE:
            updatedMessage.references = [
              ...(existingMessage.references ?? []),
              response.content,
            ];
            break;
          case ChatResponseType.MESSAGE_ID:
            updatedMessage.serverId = response.content;
            break;
        }
        next.set(messageId, updatedMessage);
        return next;
      });
    },
    [],
  );

  const handleResponse = useCallback(
    (response: ChatResponse, messageId: string): void => {
      const NON_HISTORY_TYPES = [
        ChatResponseType.STATE_UPDATE,
        ChatResponseType.CONVERSATION_ID,
      ];

      if (NON_HISTORY_TYPES.includes(response.type)) {
        _handleNonHistoryResponse(response);
      } else {
        _handleHistoryResponse(response, messageId);
      }
    },
    [_handleNonHistoryResponse, _handleHistoryResponse],
  );

  const sendMessage = useCallback(
    (text?: string): void => {
      if (!text) return;

      // Add user message to history
      addMessage({
        role: MessageRole.USER,
        content: text,
      });

      // Add empty assistant message that will be filled with the response
      const assistantResponseId = addMessage({
        role: MessageRole.ASSISTANT,
        content: "",
      });

      // Prepare chat request with conversation context
      const context = {
        ...(serverState?.state ?? {}),
        ...(conversationId ? { conversation_id: conversationId } : {}),
      };

      const chatRequest: ChatRequest = {
        message: text,
        history: mapHistoryToMessages(history),
        context,
      };

      // Send message using the new streaming hook
      chatFactory.stream(chatRequest, {
        onMessage: (response: ChatResponse) =>
          handleResponse(response as ChatResponse, assistantResponseId),
        onError: (error: string) => {
          handleResponse(
            {
              type: ChatResponseType.TEXT,
              content: error,
            },
            assistantResponseId,
          );
        },
        onClose: noop,
      });
    },
    [
      history,
      serverState,
      conversationId,
      addMessage,
      chatFactory,
      handleResponse,
    ],
  );

  const value = useMemo(
    () => ({
      history: Array.from(history.values()),
      addMessage,
      handleResponse,
      deleteMessage,
      clearHistory,
      sendMessage,
      isLoading: chatFactory.isStreaming,
      stopAnswering: chatFactory.cancel,
    }),
    [
      history,
      addMessage,
      deleteMessage,
      clearHistory,
      handleResponse,
      sendMessage,
      chatFactory.isStreaming,
      chatFactory.cancel,
    ],
  );

  return (
    <HistoryContext.Provider value={value}>{children}</HistoryContext.Provider>
  );
}
