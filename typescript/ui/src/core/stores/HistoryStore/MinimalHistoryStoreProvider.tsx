import { PropsWithChildren, useMemo } from "react";
import { createStore } from "zustand";
import { immer } from "zustand/middleware/immer";
import { HistoryStoreContext } from "./HistoryStoreContext";
import { Conversation, HistoryStore, ChatMessage } from "../../types/history";
import { RagbitsClient, MessageRole } from "@ragbits/api-client-react";
import { v4 as uuidv4 } from "uuid";

const DEFAULT_CONVERSATION_ID = "default";

const createEmptyConversation = (id: string): Conversation => ({
  conversationId: id,
  history: {},
  isLoading: false,
  lastMessageId: null,
  followupMessages: null,
  serverState: null,
  eventsLog: [],
  chatOptions: undefined,
  abortController: null,
});

/**
 * Creates a minimal HistoryStore for standalone usage without the full Ragbits backend.
 *
 * This store provides basic functionality:
 * - Single conversation
 * - Add/display messages
 * - Loading state
 * - Send messages via RagbitsClient
 *
 * For advanced features (persistence, multiple conversations, confirmations),
 * use the full HistoryStoreContextProvider with ConfigContextProvider.
 */
function createMinimalHistoryStore(
  onSendMessage?: (text: string, client: RagbitsClient) => Promise<void>,
) {
  return immer<HistoryStore>((set, get) => {
    // TODO: CREATE SHARED METHODS FOR COMMON THINGS
    const addMessageToConversation = (
      conversationId: string,
      message: Omit<ChatMessage, "id">,
    ): string => {
      const msgId = uuidv4();
      set((draft) => {
        const conv =
          draft.conversations[conversationId] ??
          createEmptyConversation(conversationId);
        conv.history[msgId] = { ...message, id: msgId };
        conv.lastMessageId = msgId;
        draft.conversations[conversationId] = conv;
      });
      return msgId;
    };

    return {
      conversations: {
        [DEFAULT_CONVERSATION_ID]: createEmptyConversation(
          DEFAULT_CONVERSATION_ID,
        ),
      },
      currentConversation: DEFAULT_CONVERSATION_ID,

      primitives: {
        getCurrentConversation: () => {
          const state = get();
          return (
            state.conversations[state.currentConversation] ??
            createEmptyConversation(state.currentConversation)
          );
        },
        addMessage: addMessageToConversation,
        deleteMessage: (conversationId, messageId) => {
          set((draft) => {
            const conv = draft.conversations[conversationId];
            if (!conv) return;
            delete conv.history[messageId];
          });
        },
        restore: () => {}, // No-op for minimal implementation
        stopAnswering: (conversationId) => {
          const conv = get().conversations[conversationId];
          conv?.abortController?.abort();
          set((draft) => {
            const c = draft.conversations[conversationId];
            if (!c) return;
            c.isLoading = false;
            c.abortController = null;
          });
        },
      },

      actions: {
        sendMessage: async (text: string, ragbitsClient: RagbitsClient) => {
          const state = get();
          const conversationId = state.currentConversation;

          // Add user message
          addMessageToConversation(conversationId, {
            role: MessageRole.User,
            content: text,
          });

          // Set loading
          set((draft) => {
            const conv = draft.conversations[conversationId];
            if (conv) {
              conv.isLoading = true;
            }
          });

          // If custom handler provided, use it
          if (onSendMessage) {
            try {
              await onSendMessage(text, ragbitsClient);
            } finally {
              set((draft) => {
                const conv = draft.conversations[conversationId];
                if (conv) {
                  conv.isLoading = false;
                }
              });
            }
            return;
          }

          // Default: just add a placeholder assistant message
          addMessageToConversation(conversationId, {
            role: MessageRole.Assistant,
            content:
              "This is a demo response. Implement onSendMessage for real API calls.",
          });

          set((draft) => {
            const conv = draft.conversations[conversationId];
            if (conv) {
              conv.isLoading = false;
            }
          });
        },

        stopAnswering: () => {
          const state = get();
          state.primitives.stopAnswering(state.currentConversation);
        },

        newConversation: () => {
          const newId = uuidv4();
          set((draft) => {
            draft.conversations[newId] = createEmptyConversation(newId);
            draft.currentConversation = newId;
          });
          return newId;
        },

        selectConversation: (conversationId: string) => {
          set((draft) => {
            draft.currentConversation = conversationId;
          });
        },

        deleteConversation: (conversationId: string) => {
          set((draft) => {
            delete draft.conversations[conversationId];
          });
        },

        // These are no-ops for minimal implementation
        sendSilentConfirmation: () => {},
        mergeExtensions: () => {},
        initializeChatOptions: () => {},
        setConversationProperties: () => {},
      },

      computed: {
        getContext: () => ({}),
      },

      _internal: {
        _hasHydrated: true,
        _setHasHydrated: () => {},
        handleResponse: () => {},
      },
    };
  });
}

export interface MinimalHistoryStoreProviderProps {
  /**
   * Optional custom message handler. If not provided, a demo response is shown.
   *
   * @example
   * onSendMessage={async (text, client) => {
   *   const response = await client.chat({ message: text });
   *   // Handle response...
   * }}
   */
  onSendMessage?: (text: string, client: RagbitsClient) => Promise<void>;
}

/**
 * A minimal HistoryStore provider for standalone usage.
 *
 * Use this when you want to render the chat UI without the full Ragbits backend setup.
 * You don't need ConfigContextProvider - it will use defaults.
 *
 * @example
 * // Basic usage (shows demo responses)
 * <MinimalHistoryStoreProvider>
 *   <Chat />
 * </MinimalHistoryStoreProvider>
 *
 * @example
 * // With custom message handling
 * <MinimalHistoryStoreProvider
 *   onSendMessage={async (text, client) => {
 *     // Your API call here
 *   }}
 * >
 *   <Chat />
 * </MinimalHistoryStoreProvider>
 */
export default function MinimalHistoryStoreProvider({
  children,
  onSendMessage,
}: PropsWithChildren<MinimalHistoryStoreProviderProps>) {
  const store = useMemo(
    () => createStore(createMinimalHistoryStore(onSendMessage)),
    [onSendMessage],
  );

  const value = useMemo(
    () => ({
      store,
      initializeUserStore: () => {}, // No-op for minimal implementation
    }),
    [store],
  );

  return (
    <HistoryStoreContext.Provider value={value}>
      {children}
    </HistoryStoreContext.Provider>
  );
}
