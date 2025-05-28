import { PropsWithChildren, useCallback, useMemo, useState } from "react";
import { HistoryContext } from "./HistoryContext.ts";
import { v4 as uuidv4 } from "uuid";
import {
  chunkMessage,
  createEventSource,
} from "../../core/utils/eventSource.ts";
import {
  ChatResponse,
  ChatResponseType,
  MessageRole,
  ServerState,
} from "../../types/api.ts";
import {
  ChatMessage,
  HistoryState,
  UnsubscribeFn,
} from "../../types/history.ts";
import { buildApiUrl, mapHistoryToMessages } from "../../core/utils/api.ts";

export function HistoryProvider({ children }: PropsWithChildren) {
  const [history, setHistory] = useState<HistoryState>(new Map());
  const [serverState, setServerState] = useState<ServerState | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [unsubscribe, setUnsubscribe] = useState<UnsubscribeFn>(null);

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
        ChatResponseType.MESSAGE_ID,
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

  const _sendMessage = useCallback(
    (text: string, assistantResponseId: string): void => {
      const context = {
        ...(serverState ?? {}),
        ...(conversationId ? { conversation_id: conversationId } : {}),
      };

      const unsubscribeFn = createEventSource(
        buildApiUrl("/api/chat"),
        (response) => handleResponse(response, assistantResponseId),
        async (error) => {
          setUnsubscribe(null);

          if (!error) return;

          const response: ChatResponse = {
            type: ChatResponseType.TEXT,
            content: error,
          };
          const chunkedResponse = chunkMessage(response);
          for await (const chunk of chunkedResponse) {
            handleResponse(chunk, assistantResponseId);
          }
        },
        () => setUnsubscribe(null),
        {
          method: "POST",
          body: {
            message: text,
            history: mapHistoryToMessages(Array.from(history.values())),
            context: context,
          },
        },
      );
      setUnsubscribe(() => unsubscribeFn);
    },
    [history, serverState, conversationId, handleResponse],
  );

  const sendMessage = useCallback(
    (text?: string): void => {
      if (!text) return;
      addMessage({
        role: MessageRole.USER,
        content: text,
      });
      const assistantResponseId = addMessage({
        role: MessageRole.ASSISTANT,
        content: "",
      });
      _sendMessage(text, assistantResponseId);
    },
    [addMessage, _sendMessage],
  );

  const stopAnswering = useCallback((): void => {
    if (!unsubscribe) return;

    unsubscribe();
    setUnsubscribe(null);
  }, [unsubscribe]);

  const value = useMemo(
    () => ({
      history: Array.from(history.values()),
      addMessage,
      handleResponse,
      deleteMessage,
      clearHistory,
      sendMessage,
      isLoading: !!unsubscribe,
      stopAnswering,
    }),
    [
      history,
      addMessage,
      deleteMessage,
      clearHistory,
      handleResponse,
      sendMessage,
      unsubscribe,
      stopAnswering,
    ],
  );

  return (
    <HistoryContext.Provider value={value}>{children}</HistoryContext.Provider>
  );
}
