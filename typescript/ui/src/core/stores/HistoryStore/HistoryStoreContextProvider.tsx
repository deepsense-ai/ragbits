import { PropsWithChildren, useMemo, useState } from "react";
import { createStore } from "zustand";
import { createHistoryStore } from "./historyStore";
import { createJSONStorage, persist } from "zustand/middleware";
import { IndexedDBStorage } from "./indexedDBStorage";
import { HistoryStoreContext } from "./HistoryStoreContext";
import { Conversation } from "../../../types/history";

export const HISTORY_STORE_KEY_BASE = "ragbits-history-store";

interface HistoryStoreContextProviderProps {
  shouldStoreHistory: boolean;
}

function initializeStore(shouldStoreHistory: boolean, storeKey: string) {
  if (shouldStoreHistory) {
    return createStore(
      persist(createHistoryStore, {
        name: storeKey,
        partialize: (value) => ({
          conversations: value.conversations,
        }),
        merge: (persistedState, currentState) => {
          const persistedConversations =
            (persistedState as Record<string, unknown>)?.conversations ?? {};
          const { conversations, currentConversation } = currentState;
          const fixedConversations = Object.values(
            persistedConversations,
          ).reduce((acc, c: Conversation) => {
            if (c.conversationId === null) {
              return acc;
            }

            acc[c.conversationId] = {
              ...c,
              isLoading: false,
              abortController: null,
            };
            return acc;
          }, {});

          return {
            ...currentState,
            currentConversation: currentConversation,
            conversations: { ...fixedConversations, ...conversations },
          };
        },
        storage: createJSONStorage(() => IndexedDBStorage),
      }),
    );
  }

  return createStore(createHistoryStore);
}

export function HistoryStoreContextProvider({
  children,
  shouldStoreHistory,
}: PropsWithChildren<HistoryStoreContextProviderProps>) {
  const [storeKey, _setStoreKey] = useState(HISTORY_STORE_KEY_BASE);
  const store = useMemo(
    () => initializeStore(shouldStoreHistory, storeKey),
    [shouldStoreHistory, storeKey],
  );

  const initializeUserStore = (userId: string) => {
    _setStoreKey(`${HISTORY_STORE_KEY_BASE}-${userId}`);
  };

  const value = useMemo(
    () => ({
      store,
      initializeUserStore,
    }),
    [store],
  );

  return (
    <HistoryStoreContext.Provider value={value}>
      {children}
    </HistoryStoreContext.Provider>
  );
}
