import {
  ChatRequest,
  ChatResponse,
  ChatResponseType,
  LiveUpdate,
  LiveUpdateType,
  MessageRole,
  RagbitsClient,
} from "@ragbits/api-client-react";
import { create } from "zustand";
import { v4 as uuidv4 } from "uuid";
import { ChatMessage, HistoryStore } from "../../types/history";
import { produce } from "immer";
import { mapHistoryToMessages } from "../utils/messageMapper";
import { API_URL } from "../../config";
import { useShallow } from "zustand/shallow";
import { createJSONStorage, persist } from "zustand/middleware";
import { omit } from "lodash";

const RAGBITS_CLIENT = new RagbitsClient({ baseUrl: API_URL });
const NON_MESSAGE_EVENTS = new Set([
  ChatResponseType.STATE_UPDATE,
  ChatResponseType.CONVERSATION_ID,
  ChatResponseType.FOLLOWUP_MESSAGES,
]);

const initialValues = () => ({
  history: new Map(),
  followupMessages: null,
  serverState: null,
  conversationId: null,
  eventsLog: [],
  isLoading: false,
  abortController: null,
  lastMessageId: null,
  context: undefined,
  chatOptions: undefined,
});

export const useHistoryStore = create<HistoryStore>()(
  persist(
    (set, get) => ({
      ...initialValues(),
      computed: {
        getContext: () => {
          const { serverState, conversationId, chatOptions } = get();
          return {
            ...(serverState ?? {}),
            ...(conversationId ? { conversation_id: conversationId } : {}),
            ...(chatOptions ? { user_settings: chatOptions } : {}),
          };
        },
      },
      _internal: {
        handleResponse: (response, messageId) => {
          const _handleLiveUpdate = (
            liveUpdate: LiveUpdate,
            message: ChatMessage,
          ) => {
            const { update_id, content, type } = liveUpdate;

            return produce(message.liveUpdates ?? new Map(), (draft) => {
              if (type === LiveUpdateType.START && draft.has(update_id)) {
                console.error(
                  `Got duplicate start event for update_id: ${update_id}. Ignoring the event.`,
                );
              }

              draft.set(update_id, content);
            });
          };

          const _handleNonMessageEvent = () => {
            set(
              produce((draft: HistoryStore) => {
                switch (response.type) {
                  case ChatResponseType.STATE_UPDATE:
                    draft.serverState = response.content;
                    break;
                  case ChatResponseType.CONVERSATION_ID:
                    draft.conversationId = response.content;
                    break;
                  case ChatResponseType.FOLLOWUP_MESSAGES:
                    draft.followupMessages = response.content;
                    break;
                }
              }),
            );
          };

          const _handleMessageEvent = () => {
            set(
              produce((draft: HistoryStore) => {
                const message = draft.history.get(messageId);
                if (!message)
                  throw new Error(
                    `Message ID ${messageId} not found in history`,
                  );

                switch (response.type) {
                  case ChatResponseType.TEXT:
                    message.content += response.content;
                    break;
                  case ChatResponseType.REFERENCE:
                    message.references = [
                      ...(message.references ?? []),
                      response.content,
                    ];
                    break;
                  case ChatResponseType.MESSAGE_ID:
                    message.serverId = response.content;
                    break;
                  case ChatResponseType.LIVE_UPDATE:
                    message.liveUpdates = _handleLiveUpdate(
                      response.content,
                      message,
                    );
                    break;
                }
              }),
            );
          };

          if (NON_MESSAGE_EVENTS.has(response.type)) {
            _handleNonMessageEvent();
          } else {
            _handleMessageEvent();
          }

          set(
            produce((draft: HistoryStore) => {
              draft.eventsLog[draft.eventsLog.length - 1].push(response);
            }),
          );
        },
      },

      primitives: {
        addMessage: (message) => {
          const id = uuidv4();
          const newMessage: ChatMessage = { ...message, id };
          set(
            produce((draft: HistoryStore) => {
              draft.followupMessages = null;
              draft.lastMessageId = id;
              draft.history.set(id, newMessage);
            }),
          );
          return id;
        },

        deleteMessage: (messageId) => {
          set(
            produce((draft: HistoryStore) => {
              const { history } = get();
              const messageIds = Array.from(history.keys());

              if (messageIds.at(-1) === messageId) {
                draft.lastMessageId = messageIds.at(-2) ?? null;
              }

              draft.history.delete(messageId);
            }),
          );
        },
      },

      actions: {
        mergeExtensions: (messageId, extensions) => {
          set(
            produce((draft: HistoryStore) => {
              if (!draft.history.has(messageId)) {
                throw new Error(
                  "Attempted to set extensions for a message that does not exist.",
                );
              }

              const existingMessage = draft.history.get(messageId)!;
              existingMessage.extensions = {
                ...existingMessage.extensions,
                ...extensions,
              };
              draft.history.set(messageId, existingMessage);
            }),
          );
        },
        initializeChatOptions: (defaultOptions) => {
          set(
            produce((draft: HistoryStore) => {
              const currentOptions = draft.chatOptions ?? {};
              Object.keys(currentOptions).forEach((key) => {
                if (
                  !Object.prototype.hasOwnProperty.call(defaultOptions, key)
                ) {
                  delete currentOptions[key];
                }
              });

              Object.keys(defaultOptions).forEach((key) => {
                if (
                  !Object.prototype.hasOwnProperty.call(currentOptions, key)
                ) {
                  currentOptions[key] = defaultOptions[key];
                }
              });

              draft.chatOptions = currentOptions;
            }),
          );
        },
        setChatOptions: (options) => {
          set(
            produce((draft: HistoryStore) => {
              draft.chatOptions = options;
            }),
          );
        },
        stopAnswering: () => get().abortController?.abort(),

        clearHistory: () => {
          set((store) => ({
            ...store,
            ...omit(initialValues(), "chatOptions"),
          }));
        },

        sendMessage: (text) => {
          const {
            _internal: { handleResponse },
            primitives: { addMessage },
            computed: { getContext },
            history,
          } = get();

          addMessage({
            role: MessageRole.USER,
            content: text,
          });

          // Add empty assistant message that will be filled with the response
          const assistantResponseId = addMessage({
            role: MessageRole.ASSISTANT,
            content: "",
          });

          const chatRequest: ChatRequest = {
            message: text,
            history: mapHistoryToMessages(history),
            context: getContext(),
          };

          // Add new entry for events
          set(
            produce((draft: HistoryStore) => {
              draft.eventsLog.push([]);
            }),
          );

          const abortController = new AbortController();
          set(
            produce((draft: HistoryStore) => {
              draft.abortController = abortController;
              draft.isLoading = true;
            }),
          );

          const handleStreamEnd = () => {
            set(
              produce((draft: HistoryStore) => {
                draft.abortController = null;
                draft.isLoading = false;
              }),
            );
          };

          RAGBITS_CLIENT.makeStreamRequest(
            "/api/chat",
            chatRequest,
            {
              onMessage: (response: ChatResponse) =>
                handleResponse(response, assistantResponseId),
              onError: (error: Error) => {
                handleResponse(
                  {
                    type: ChatResponseType.TEXT,
                    content: error.message,
                  },
                  assistantResponseId,
                );
                handleStreamEnd();
              },
              onClose: handleStreamEnd,
            },
            abortController.signal,
          );
        },
      },
    }),
    {
      name: "ragbits-history-store",
      // Using partialize to only persist the chatOptions, we might want to expand this in the future
      // when conversation history is supported
      partialize: (value) => ({ chatOptions: value.chatOptions }),
      storage: createJSONStorage(() => localStorage),
    },
  ),
);

export const useHistoryActions = () => useHistoryStore((s) => s.actions);
export const useHistoryPrimitives = () => useHistoryStore((s) => s.primitives);
export const useHistoryComputed = () => useHistoryStore((s) => s.computed);
export const useMessage = (messageId: string | undefined | null) =>
  useHistoryStore((s) => (messageId ? s.history.get(messageId) : undefined));
export const useMessageIds = () =>
  useHistoryStore(useShallow((s) => Array.from(s.history.keys())));
export const useMessages = () =>
  useHistoryStore(useShallow((s) => Array.from(s.history.values())));
