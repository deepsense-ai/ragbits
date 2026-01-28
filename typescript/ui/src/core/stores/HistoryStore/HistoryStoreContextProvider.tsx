import { PropsWithChildren, useMemo } from "react";
import { createStore, useStore } from "zustand";
import { immer } from "zustand/middleware/immer";
import { HistoryStoreContext } from "./HistoryStoreContext";
import { HistoryStore, ChatMessage } from "../../types/history";
import { MessageRole } from "@ragbits/api-client-react";
import { v4 as uuidv4 } from "uuid";
import InitializationScreen from "../../components/InitializationScreen";
import {
  initialConversationValues,
  initialHistoryValues,
  isTemporaryConversation,
  updateConversation,
} from "./utils";
import { omitBy } from "lodash";

const createMinimalHistoryStore = immer<HistoryStore>((set, get) => {
  return {
    ...initialHistoryValues(),
    // TODO: We might want to unify primitives with the RagbitsHistoryStore later
    primitives: {
      getCurrentConversation: () => {
        const { currentConversation, conversations } = get();
        const conversation = conversations[currentConversation];

        if (!conversation) {
          throw new Error("Tried to get conversation that doesn't exist.");
        }

        return conversation;
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
      restore: () => {}, // No-op for minimal implementation
      stopAnswering: (conversationId) => {
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
      sendMessage: async (text: string) => {
        const state = get();
        const {
          primitives: { addMessage },
        } = get();
        const conversationId = state.currentConversation;

        // Add user message
        addMessage(conversationId, {
          role: MessageRole.User,
          content: text,
        });

        // Set loading
        set(
          updateConversation(conversationId, (draft) => {
            draft.isLoading = true;
          }),
        );

        // Default: just add a placeholder assistant message
        addMessage(conversationId, {
          role: MessageRole.Assistant,
          content:
            "This is a demo response. Use RagbitsHistoryStoreProvider for real API calls.",
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

      selectConversation: (conversationId: string) => {
        set((draft) => {
          if (draft.currentConversation === conversationId) {
            return;
          }
          const conversation = draft.conversations[conversationId];
          if (!conversation) {
            throw new Error(
              `Tried to select conversation that doesn't exist, id: ${conversationId}`,
            );
          }

          draft.currentConversation = conversationId;
        });
      },

      deleteConversation: (conversationId: string) => {
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

export type HistoryStoreInitializer = typeof createMinimalHistoryStore;

export interface HistoryStoreContextProviderProps {
  storeInitializer?: HistoryStoreInitializer;
  waitForHydration?: boolean;
}

export default function HistoryStoreContextProvider({
  children,
  storeInitializer = createMinimalHistoryStore,
  waitForHydration = false,
}: PropsWithChildren<HistoryStoreContextProviderProps>) {
  const store = useMemo(
    () => createStore(storeInitializer),
    [storeInitializer],
  );
  const hasHydrated = useStore(store, (s) => s._internal._hasHydrated);

  const value = useMemo(
    () => ({
      store,
    }),
    [store],
  );

  if (waitForHydration && !hasHydrated) {
    return <InitializationScreen />;
  }

  return (
    <HistoryStoreContext.Provider value={value}>
      {children}
    </HistoryStoreContext.Provider>
  );
}
