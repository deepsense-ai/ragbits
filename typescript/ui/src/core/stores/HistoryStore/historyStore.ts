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
import { v4 as uuidv4 } from "uuid";
import {
  ChatMessage,
  Conversation,
  HistoryStore,
} from "../../../types/history";
import { produce } from "immer";
import { mapHistoryToMessages } from "../../utils/messageMapper";
import { API_URL } from "../../../config";
import { immer } from "zustand/middleware/immer";
import { omitBy } from "lodash";

const TEMPORARY_CONVERSATION_TAG = "temp-";
const RAGBITS_CLIENT = new RagbitsClient({ baseUrl: API_URL });
const NON_MESSAGE_EVENTS = new Set([
  ChatResponseType.STATE_UPDATE,
  ChatResponseType.CONVERSATION_ID,
  ChatResponseType.FOLLOWUP_MESSAGES,
]);

const getTemoraryConversationId = () =>
  `${TEMPORARY_CONVERSATION_TAG}${uuidv4()}`;

const initialConversationValues = () => ({
  history: {},
  followupMessages: null,
  serverState: null,
  conversationId: getTemoraryConversationId(),
  eventsLog: [],
  lastMessageId: null,
  context: undefined,
  chatOptions: undefined,
  isLoading: false,
  abortController: null,
});

const initialHistoryValues = () => {
  // Always initialize with empty conversation
  const startingConversation = initialConversationValues();
  return {
    conversations: {
      [startingConversation.conversationId]: startingConversation,
    },
    currentConversation: startingConversation.conversationId,
  };
};

const updateConversation = (
  conversationId: string,
  mutator: (draft: Conversation) => void,
) => {
  return (draft: HistoryStore) => {
    // `null` is a special key for conversations that don't have a server-assigned ID yet.
    // Only one such conversation can exist at any time, as they all share the same key.
    const conversation = draft.conversations[conversationId];

    if (!conversation) {
      throw new Error(
        `Conversation with ID '${conversationId}' does not exist`,
      );
    }

    mutator(conversation);
  };
};

export const isTemporaryConversation = (conversation: Conversation) => {
  return conversation.conversationId.startsWith(TEMPORARY_CONVERSATION_TAG);
};

export const createHistoryStore = immer<HistoryStore>((set, get) => ({
  ...initialHistoryValues(),
  computed: {
    getContext: () => {
      const {
        primitives: { getCurrentConversation },
      } = get();
      const conversation = getCurrentConversation();
      const { serverState, conversationId, chatOptions } = conversation;
      return {
        ...(serverState ?? {}),
        ...(conversationId && !isTemporaryConversation(conversation)
          ? { conversation_id: conversationId }
          : {}),
        ...(chatOptions ? { user_settings: chatOptions } : {}),
      };
    },
  },
  _internal: {
    handleResponse: (conversationId, messageId, response) => {
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
          updateConversation(conversationId, (draft) => {
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
          set((draft) => {
            const oldConversation = draft.conversations[conversationId];

            if (!oldConversation) {
              throw new Error("Received events for non-existent conversation");
            }

            oldConversation.conversationId = content;
          });
        }
      };

      const _handleMessageEvent = () => {
        set(
          updateConversation(conversationId, (draft) => {
            const message = draft.history[messageId];
            if (!message)
              throw new Error(`Message ID ${messageId} not found in history`);

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
        updateConversation(conversationId, (draft) => {
          draft.eventsLog[draft.eventsLog.length - 1].push(response);
        }),
      );
    },
  },

  primitives: {
    getCurrentConversation: () => {
      const { currentConversation, conversations } = get();
      const conversation = conversations[currentConversation];

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
      // Copied conversation should be treated as temporary one, it would get it's own
      // id after first message
      const conversationId = getTemoraryConversationId();
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
        draft.conversations[conversationId] = conversation;
        draft.currentConversation = conversationId;
      });
    },

    addMessage: (conversationId, message) => {
      const id = uuidv4();
      const newMessage: ChatMessage = { ...message, id };
      set(
        updateConversation(conversationId, (draft) => {
          draft.followupMessages = null;
          draft.lastMessageId = id;
          draft.history[id] = newMessage;
        }),
      );
      return id;
    },

    deleteMessage: (conversationId, messageId) => {
      set(
        updateConversation(conversationId, (draft) => {
          const { history } = draft;
          const messageIds = Object.keys(history);

          if (messageIds.at(-1) === messageId) {
            draft.lastMessageId = messageIds.at(-2) ?? null;
          }

          delete draft.history[messageId];
        }),
      );
    },

    stopAnswering: (conversationId: string) => {
      const conversation = get().conversations[conversationId];

      if (!conversation) {
        throw new Error(
          "Tried to stop answering for conversation that doesn't exist",
        );
      }

      conversation.abortController?.abort();
      set(
        updateConversation(conversationId, (draft) => {
          draft.abortController = null;
          draft.isLoading = false;
        }),
      );
    },
  },

  actions: {
    selectConversation: (conversationId) => {
      set((draft) => {
        const conversation = draft.conversations[conversationId];
        if (!conversation) {
          throw new Error(
            `Tried to select conversation that doesn't exist, id: ${conversationId}`,
          );
        }

        draft.currentConversation = conversationId;
      });
    },
    deleteConversation: (conversationId) => {
      const {
        actions: { newConversation },
        primitives: { stopAnswering },
        currentConversation,
      } = get();
      stopAnswering(conversationId);

      if (conversationId === currentConversation) {
        newConversation();
      }

      set((draft) => {
        delete draft.conversations[conversationId];
      });
    },
    mergeExtensions: (messageId, extensions) => {
      const { currentConversation } = get();
      set(
        updateConversation(currentConversation, (draft) => {
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
      const { currentConversation } = get();
      set(
        updateConversation(currentConversation, (draft) => {
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
      const { currentConversation } = get();
      set(
        updateConversation(currentConversation, (draft) => {
          draft.chatOptions = options;
        }),
      );
    },

    stopAnswering: () => {
      const {
        currentConversation,
        primitives: { stopAnswering },
      } = get();
      stopAnswering(currentConversation);
    },

    newConversation: () => {
      set((draft) => {
        const newConversation = initialConversationValues();
        draft.conversations[newConversation.conversationId] = newConversation;
        draft.currentConversation = newConversation.conversationId;

        // Cleanup unused temporary conversations
        draft.conversations = omitBy(
          draft.conversations,
          (c) =>
            isTemporaryConversation(c) &&
            c.conversationId !== draft.currentConversation,
        );
      });
    },

    sendMessage: (text) => {
      const {
        _internal: { handleResponse },
        primitives: { addMessage, getCurrentConversation },
        computed: { getContext },
        actions: { stopAnswering },
      } = get();

      const { history, conversationId } = getCurrentConversation();
      addMessage(conversationId, {
        role: MessageRole.USER,
        content: text,
      });

      // Add empty assistant message that will be filled with the response
      const assistantResponseId = addMessage(conversationId, {
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
        updateConversation(conversationId, (draft) => {
          draft.eventsLog.push([]);
        }),
      );

      const abortController = new AbortController();
      set(
        updateConversation(conversationId, (draft) => {
          draft.abortController = abortController;
          draft.isLoading = true;
        }),
      );

      const updateIdentifier = () => {
        set((draft) => {
          // While streaming, we use a temporary identifier as the key.
          // When the stream finishes, we replace it with the final identifier stored in the object,
          // which is then used as the key in the `conversations` record.
          const conversation = draft.conversations[conversationId];
          if (!conversation) {
            // Silently ignore conversations that don't exist
            return;
          }

          // We have to reset currentConversation if it's the active one
          if (draft.currentConversation === conversationId) {
            draft.currentConversation = conversation.conversationId;
          }

          draft.conversations[conversation.conversationId] = conversation;
          delete draft.conversations[conversationId];
        });
      };

      RAGBITS_CLIENT.makeStreamRequest(
        "/api/chat",
        chatRequest,
        {
          onMessage: (response: ChatResponse) =>
            handleResponse(conversationId, assistantResponseId, response),
          onError: (error: Error) => {
            handleResponse(conversationId, assistantResponseId, {
              type: ChatResponseType.TEXT,
              content: error.message,
            });
            stopAnswering();
            updateIdentifier();
          },
          onClose: () => {
            stopAnswering();
            updateIdentifier();
          },
        },
        abortController.signal,
      );
    },
  },
}));
