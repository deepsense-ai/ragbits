import {
  PropsWithChildren,
  useCallback,
  useMemo,
  useRef,
  useState,
} from "react";
import { HistoryContext } from "./HistoryContext.ts";
import { v4 as uuidv4 } from "uuid";
import {
  TypedChatResponse as ChatResponse,
  ChatResponseType,
  MessageRole,
  ServerState,
  useRagbitsStream,
  ChatRequest,
  LiveUpdate,
  LiveUpdateType,
} from "@ragbits/api-client-react";
import { ChatMessage, HistoryState } from "../../../types/history.ts";
import { mapHistoryToMessages } from "../../utils/messageMapper.ts";
import { noop } from "lodash";

export function HistoryProvider({ children }: PropsWithChildren) {
  const [history, setHistory] = useState<HistoryState>(new Map());
  /**
   * Gather log of all events in the chat.
   * Using ref instead of state to avoid copying
   */
  const eventsLogRef = useRef<ChatResponse[][]>([]);
  const [followupMessages, setFollowupMessages] = useState<string[] | null>(
    null,
  );
  const [serverState, setServerState] = useState<ServerState | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const chatFactory = useRagbitsStream("/api/chat");
  const context = useMemo(
    () => ({
      ...(serverState ?? {}),
      ...(conversationId ? { conversation_id: conversationId } : {}),
    }),
    [conversationId, serverState],
  );

  const updateHistoryState = (
    updater: (prev: HistoryState) => HistoryState,
  ) => {
    setHistory((prev) => updater(prev));
  };

  const addMessage = useCallback((message: Omit<ChatMessage, "id">): string => {
    const id = uuidv4();
    const newMessage: ChatMessage = { ...message, id };
    setFollowupMessages(null);
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
    eventsLogRef.current = [];
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
        case ChatResponseType.FOLLOWUP_MESSAGES:
          setFollowupMessages(response.content);
          break;
      }
    },
    [],
  );

  const _handleLiveUpdate = useCallback(
    (liveUpdate: LiveUpdate, message: ChatMessage) => {
      const { update_id, content, type } = liveUpdate;

      const existingUpdates = message.liveUpdates ?? new Map();
      const newUpdates = new Map(existingUpdates);

      const isKnown = newUpdates.has(update_id);

      if (type === LiveUpdateType.START && isKnown) {
        console.error(
          `Got duplicate start event for update_id: ${update_id}. Ignoring the event.`,
        );

        return newUpdates;
      }

      newUpdates.set(update_id, content);

      return newUpdates;
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
          case ChatResponseType.LIVE_UPDATE:
            updatedMessage.liveUpdates = _handleLiveUpdate(
              response.content,
              updatedMessage,
            );
            break;
        }
        next.set(messageId, updatedMessage);
        return next;
      });
    },
    [_handleLiveUpdate],
  );

  const handleResponse = useCallback(
    (response: ChatResponse, messageId: string): void => {
      const NON_HISTORY_TYPES = [
        ChatResponseType.STATE_UPDATE,
        ChatResponseType.CONVERSATION_ID,
        ChatResponseType.FOLLOWUP_MESSAGES,
      ];

      if (NON_HISTORY_TYPES.includes(response.type)) {
        _handleNonHistoryResponse(response);
      } else {
        _handleHistoryResponse(response, messageId);
      }

      const eventsLog = eventsLogRef.current;
      eventsLog[eventsLog.length - 1].push(response);
    },
    [_handleNonHistoryResponse, _handleHistoryResponse],
  );

  const sendMessage = useCallback(
    (text: string, options?: Record<string, unknown>): void => {
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
        ...(serverState ?? {}),
        ...(conversationId ? { conversation_id: conversationId } : {}),
        ...(options ?? {}), // Include chat options in context
      };

      const chatRequest: ChatRequest = {
        message: text,
        history: mapHistoryToMessages(history),
        context,
      };

      // Add new entry for events
      eventsLogRef.current.push([]);

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
    [addMessage, history, context, chatFactory, handleResponse],
  );

  const value = useMemo(
    () => ({
      history: Array.from(history.values()),
      followupMessages,
      isLoading: chatFactory.isStreaming,
      eventsLog: eventsLogRef.current,
      context,
      addMessage,
      handleResponse,
      deleteMessage,
      clearHistory,
      sendMessage,
      stopAnswering: chatFactory.cancel,
    }),
    [
      history,
      followupMessages,
      chatFactory.isStreaming,
      chatFactory.cancel,
      context,
      addMessage,
      handleResponse,
      deleteMessage,
      clearHistory,
      sendMessage,
    ],
  );

  return (
    <HistoryContext.Provider value={value}>{children}</HistoryContext.Provider>
  );
}
