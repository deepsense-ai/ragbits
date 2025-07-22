import {
  ChatRequest,
  ChatResponse,
  ChatResponseType,
  LiveUpdate,
  LiveUpdateType,
  MessageRole,
  RagbitsClient,
  Image,
} from "@ragbits/api-client-react";
import { create } from "zustand";
import { v4 as uuidv4 } from "uuid";
import { ChatMessage, Conversation, HistoryStore } from "../../types/history";
import { produce } from "immer";
import { mapHistoryToMessages } from "../utils/messageMapper";
import { API_URL } from "../../config";
import { useShallow } from "zustand/shallow";
import { createJSONStorage, persist, StateStorage } from "zustand/middleware";
import { immer } from "zustand/middleware/immer";
import { get, set, del } from "idb-keyval";

const IndexedDBStorage: StateStorage = {
  getItem: async (name: string): Promise<string | null> => {
    return (await get(name)) || null;
  },
  setItem: async (name: string, value: string): Promise<void> => {
    await set(name, value);
  },
  removeItem: async (name: string): Promise<void> => {
    await del(name);
  },
};

const RAGBITS_CLIENT = new RagbitsClient({ baseUrl: API_URL });
const NON_MESSAGE_EVENTS = new Set([
  ChatResponseType.STATE_UPDATE,
  ChatResponseType.CONVERSATION_ID,
  ChatResponseType.FOLLOWUP_MESSAGES,
]);

const initialHistoryValues = () => ({
  conversations: {},
  currentConversation: null,
  isLoading: false,
  abortController: null,
});

const initialConversationValues = () => ({
  history: {},
  followupMessages: null,
  serverState: null,
  conversationId: null,
  eventsLog: [],
  lastMessageId: null,
  context: undefined,
  chatOptions: undefined,
});

export const getConversationKey = (conversationId: string | null) =>
  `${conversationId}`;
const updateConversation = (mutator: (draft: Conversation) => void) => {
  return (draft: HistoryStore) => {
    // `null` is a speciall key for conversations that don't have server assigned id yet
    // There could only be one conversation without an id at any given time as they have the same key
    const conversation =
      draft.conversations[getConversationKey(draft.currentConversation)];

    if (!conversation) {
      throw new Error(
        `Conversation with ${draft.currentConversation} id doesn't exist`,
      );
    }

    mutator(conversation);
  };
};

export const useHistoryStore = create<HistoryStore>()(
  immer(
    persist(
      (set, get) => ({
        ...initialHistoryValues(),
        computed: {
          getContext: () => {
            const {
              primitives: { getCurrentConversation },
            } = get();
            const { serverState, conversationId, chatOptions } =
              getCurrentConversation();
            return {
              ...(serverState ?? {}),
              ...(conversationId ? { conversation_id: conversationId } : {}),
              ...(chatOptions ? { user_settings: chatOptions } : {}),
            };
          },
        },
        _internal: {
          handleResponse: (response, messageId) => {
            const _handleImage = (image: Image, message: ChatMessage) => {
              return produce(message.images ?? {}, (draft) => {
                if (draft[image.id]) {
                  console.error(
                    `Got duplicate image event for image_id: ${image.id}. Ignoring the event.`,
                  );
                }

                draft[image.id] = image.url;
              });
            };

            const _handleLiveUpdate = (
              liveUpdate: LiveUpdate,
              message: ChatMessage,
            ) => {
              const { update_id, content, type } = liveUpdate;

              return produce(message.liveUpdates ?? {}, (draft) => {
                if (type === LiveUpdateType.START && update_id in draft) {
                  console.error(
                    `Got duplicate start event for update_id: ${update_id}. Ignoring the event.`,
                  );
                }

                draft[update_id] = content;
              });
            };

            const _handleNonMessageEvent = () => {
              const { type, content } = response;
              set(
                updateConversation((draft) => {
                  switch (type) {
                    case ChatResponseType.STATE_UPDATE:
                      draft.serverState = content;
                      break;
                    case ChatResponseType.CONVERSATION_ID:
                      draft.conversationId = content;
                      break;
                    case ChatResponseType.FOLLOWUP_MESSAGES:
                      draft.followupMessages = content;
                      break;
                  }
                }),
              );

              if (type === ChatResponseType.CONVERSATION_ID) {
                const newKey = getConversationKey(content);

                set((draft) => {
                  const oldKey = getConversationKey(draft.currentConversation);
                  const oldConversation = draft.conversations[oldKey];

                  if (!oldConversation) {
                    throw new Error(
                      "Received events for non-existent conversation",
                    );
                  }

                  delete draft.conversations[oldKey];
                  draft.conversations[newKey] = oldConversation;
                  draft.currentConversation = content;
                });
              }
            };

            const _handleMessageEvent = () => {
              set(
                updateConversation((draft) => {
                  const message = draft.history[messageId];
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
                    case ChatResponseType.IMAGE:
                      message.images = _handleImage(response.content, message);
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
              updateConversation((draft) => {
                draft.eventsLog[draft.eventsLog.length - 1].push(response);
              }),
            );
          },
        },

        primitives: {
          getCurrentConversation: () => {
            set((draft) => {
              const key = getConversationKey(draft.currentConversation);

              if (key in draft.conversations) {
                return;
              }

              draft.conversations[key] = {
                ...initialConversationValues(),
              };
            });

            const { currentConversation, conversations } = get();
            const key = getConversationKey(currentConversation);
            const conversation = conversations[key];

            if (!conversation) {
              throw new Error("Tried to get conversation that doesn't exist.");
            }

            return conversation;
          },
          restore: (
            history: Conversation["history"],
            followupMessages: Conversation["followupMessages"],
            chatOptions: Conversation["chatOptions"],
            serverState: Conversation["serverState"],
          ) => {
            // Copied conversation should be treated as a new one, it would get it's own
            // id after first message
            const conversationId = null;
            const conversation: Conversation = {
              ...initialConversationValues(),
              followupMessages,
              chatOptions,
              serverState,
              history,
              conversationId,
            };
            const nonUserMessages = Object.values(history).filter(
              (m) => m.role !== MessageRole.USER,
            );
            conversation.eventsLog = nonUserMessages.map(() => []);
            set((draft: HistoryStore) => {
              draft.conversations[getConversationKey(conversationId)] =
                conversation;
              draft.currentConversation = conversationId;
            });
          },

          addMessage: (message) => {
            const id = uuidv4();
            const newMessage: ChatMessage = { ...message, id };
            set(
              updateConversation((draft) => {
                draft.followupMessages = null;
                draft.lastMessageId = id;
                draft.history[id] = newMessage;
              }),
            );
            return id;
          },

          deleteMessage: (messageId) => {
            set(
              updateConversation((draft) => {
                const { history } = draft;
                const messageIds = Object.keys(history);

                if (messageIds.at(-1) === messageId) {
                  draft.lastMessageId = messageIds.at(-2) ?? null;
                }

                delete draft.history[messageId];
              }),
            );
          },
        },

        actions: {
          selectConversation: (conversationKey) => {
            const {
              actions: { stopAnswering },
            } = get();

            stopAnswering();

            set((draft) => {
              if (!(conversationKey in draft.conversations)) {
                throw new Error(
                  `Tried to select conversation that doesn't exist, id: ${conversationKey}`,
                );
              }

              draft.currentConversation = conversationKey;
            });
          },
          deleteConversation: (convKey) => {
            set((draft) => {
              if (convKey === getConversationKey(draft.currentConversation)) {
                const {
                  actions: { stopAnswering },
                } = get();

                stopAnswering();
                draft.currentConversation = null;
              }
              delete draft.conversations[getConversationKey(convKey)];
            });
          },
          mergeExtensions: (messageId, extensions) => {
            set(
              updateConversation((draft) => {
                if (!(messageId in draft.history)) {
                  throw new Error(
                    "Attempted to set extensions for a message that does not exist.",
                  );
                }

                const existingMessage = draft.history[messageId];
                existingMessage.extensions = {
                  ...existingMessage.extensions,
                  ...extensions,
                };
                draft.history[messageId] = existingMessage;
              }),
            );
          },

          initializeChatOptions: (defaultOptions) => {
            set(
              updateConversation((draft) => {
                const currentOptions = draft.chatOptions ?? {};
                Object.keys(currentOptions).forEach((key) => {
                  if (!(key in defaultOptions)) {
                    delete currentOptions[key];
                  }
                });

                Object.keys(defaultOptions).forEach((key) => {
                  if (!(key in currentOptions)) {
                    currentOptions[key] = defaultOptions[key];
                  }
                });

                draft.chatOptions = currentOptions;
              }),
            );
          },
          setChatOptions: (options) => {
            set(
              updateConversation((draft) => {
                draft.chatOptions = options;
              }),
            );
          },

          stopAnswering: () => {
            get().abortController?.abort();
            set((draft) => {
              draft.abortController = null;
              draft.isLoading = false;
            });
          },

          clearHistory: () => {
            set((draft) => {
              draft.currentConversation = null;
              draft.conversations[
                getConversationKey(draft.currentConversation)
              ] = {
                ...initialConversationValues(),
              };
            });
          },

          sendMessage: (text) => {
            const {
              _internal: { handleResponse },
              primitives: { addMessage, getCurrentConversation },
              computed: { getContext },
              actions: { stopAnswering },
            } = get();

            const { history } = getCurrentConversation();
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
              updateConversation((draft) => {
                draft.eventsLog.push([]);
              }),
            );

            const abortController = new AbortController();
            set((draft: HistoryStore) => {
              draft.abortController = abortController;
              draft.isLoading = true;
            });

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
                  stopAnswering();
                },
                onClose: stopAnswering,
              },
              abortController.signal,
            );
          },
        },
      }),
      {
        name: "ragbits-history-store",
        partialize: (value) => ({
          conversations: value.conversations,
        }),
        storage: createJSONStorage(() => IndexedDBStorage),
      },
    ),
  ),
);

export const useHistoryActions = () => useHistoryStore((s) => s.actions);
export const useHistoryPrimitives = () => useHistoryStore((s) => s.primitives);
export const useHistoryComputed = () => useHistoryStore((s) => s.computed);
export const useConversationProperty = <T>(
  selector: (s: Conversation) => T,
): T =>
  useHistoryStore(
    useShallow((s) => selector(s.primitives.getCurrentConversation())),
  );
export const useMessage = (messageId: string | undefined | null) =>
  useHistoryStore((s) =>
    messageId
      ? s.primitives.getCurrentConversation().history[messageId]
      : undefined,
  );
export const useMessageIds = () =>
  useHistoryStore(
    useShallow((s) =>
      Object.keys(s.primitives.getCurrentConversation().history),
    ),
  );
export const useMessages = () =>
  useHistoryStore(
    useShallow((s) =>
      Object.values(s.primitives.getCurrentConversation().history),
    ),
  );
