import {
  ChatRequest,
  ChatResponse,
  MessageRole,
} from "@ragbits/api-client-react";
import { v4 as uuidv4 } from "uuid";
import {
  ChatMessage,
  Conversation,
  HistoryStore,
} from "../../../types/history";
import { mapHistoryToMessages } from "../../utils/messageMapper";
import { immer } from "zustand/middleware/immer";
import { omitBy } from "lodash";
import { ChatHandlerRegistry } from "./eventHandlers/eventHandlerRegistry";

const TEMPORARY_CONVERSATION_TAG = "temp-";

const getTemporaryConversationId = () =>
  `${TEMPORARY_CONVERSATION_TAG}${uuidv4()}`;

const initialConversationValues = () => ({
  history: {},
  followupMessages: null,
  serverState: null,
  conversationId: getTemporaryConversationId(),
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
    const conversation = draft.conversations[conversationId];
    if (!conversation) {
      throw new Error(
        `Conversation with ID '${conversationId}' does not exist`,
      );
    }

    mutator(conversation);
  };
};

export const isTemporaryConversation = (conversationId: string) => {
  return conversationId.startsWith(TEMPORARY_CONVERSATION_TAG);
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
        ...(conversationId &&
        !isTemporaryConversation(conversation.conversationId)
          ? { conversation_id: conversationId }
          : {}),
        ...(chatOptions ? { user_settings: chatOptions } : {}),
      };
    },
  },
  _internal: {
    _hasHydrated: false,
    _setHasHydrated: (state) => {
      set((draft) => {
        draft._internal._hasHydrated = state;
      });
    },
    handleResponse: (conversationIdRef, messageId, response) => {
      let additionalContext: object | void = undefined;
      const handlers = ChatHandlerRegistry.get(response.type);

      set(
        updateConversation(conversationIdRef.current, (draft) => {
          const message = draft.history[messageId];
          if (!message)
            throw new Error(`Message ID ${messageId} not found in history`);

          additionalContext = handlers.handle(response, draft, {
            conversationIdRef,
            messageId,
          });
        }),
      );

      set((draft) => {
        handlers.after?.(response, draft, {
          conversationIdRef,
          messageId,
          ...additionalContext,
        });
      });

      set(
        updateConversation(conversationIdRef.current, (draft) => {
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
      const conversationId = getTemporaryConversationId();
      const conversation: Conversation = {
        ...initialConversationValues(),
        followupMessages,
        chatOptions,
        serverState,
        history,
        conversationId,
      };
      const nonUserMessages = Object.values(history).filter(
        (m) => m.role !== MessageRole.User,
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

      set((draft) => {
        delete draft.conversations[conversationId];
      });

      if (conversationId === currentConversation) {
        return newConversation();
      }
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
    setConversationProperties: (conversationKey, properties) => {
      set(
        updateConversation(conversationKey, (draft) => {
          Object.assign(draft, properties);
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
      const newConversation = initialConversationValues();
      set((draft) => {
        draft.conversations[newConversation.conversationId] = newConversation;
        draft.currentConversation = newConversation.conversationId;

        // Cleanup unused temporary conversations
        draft.conversations = omitBy(
          draft.conversations,
          (c) =>
            isTemporaryConversation(c.conversationId) &&
            c.conversationId !== draft.currentConversation,
        );
      });

      return newConversation.conversationId;
    },

    sendMessage: (text, ragbitsClient) => {
      const {
        _internal: { handleResponse },
        primitives: { addMessage, getCurrentConversation, stopAnswering },
        computed: { getContext },
      } = get();

      const { history, conversationId } = getCurrentConversation();
      addMessage(conversationId, {
        role: MessageRole.User,
        content: text,
      });

      // Add empty assistant message that will be filled with the response
      const assistantResponseId = addMessage(conversationId, {
        role: MessageRole.Assistant,
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
      const conversationIdRef = { current: conversationId };

      set(
        updateConversation(conversationId, (draft) => {
          draft.abortController = abortController;
          draft.isLoading = true;
        }),
      );

      ragbitsClient.makeStreamRequest(
        "/api/chat",
        chatRequest,
        {
          onMessage: (response: ChatResponse) =>
            handleResponse(conversationIdRef, assistantResponseId, response),
          onError: (error: Error) => {
            handleResponse(conversationIdRef, assistantResponseId, {
              type: "text",
              content: { text: error.message },
            });
            stopAnswering(conversationIdRef.current);
          },
          onClose: () => {
            stopAnswering(conversationIdRef.current);
          },
        },
        abortController.signal,
      );
    },
  },
}));
