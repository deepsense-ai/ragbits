import { PropsWithChildren, useCallback, useMemo, useState } from "react";
import { createStore, useStore } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import { HistoryStoreContext } from "../../../core/stores/HistoryStore/HistoryStoreContext";
import { Conversation } from "../../../core/types/history";
import InitializationScreen from "../../../core/components/InitializationScreen";
import { createHistoryStore } from "./historyStore";
import { IndexedDBStorage } from "./indexedDBStorage";
import { useConfig } from "../../../core/contexts/ConfigContext/ConfigContext";

export const HISTORY_STORE_KEY_BASE = "ragbits-history-store";

function initializeStore(shouldStoreHistory: boolean, storeKey: string) {
  if (shouldStoreHistory) {
    return createStore(
      persist(createHistoryStore, {
        name: storeKey,
        partialize: (value) => ({
          conversations: value.conversations,
        }),
        onRehydrateStorage: (state) => {
          // We have to wait for the hydration to finish to avoid any races that may result in saving of the invalid
          // state to the storage (e.g. clearing all history)
          return () => state._internal._setHasHydrated(true);
        },
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

  const store = createStore(createHistoryStore);
  store.getState()._internal._setHasHydrated(true);

  return store;
}

export default function RagbitsHistoryStoreProvider({
  children,
}: PropsWithChildren) {
  const [storeKey, setStoreKey] = useState(HISTORY_STORE_KEY_BASE);
  const {
    config: { conversation_history: shouldStoreHistory },
  } = useConfig();
  const store = useMemo(
    () => initializeStore(shouldStoreHistory, storeKey),
    [shouldStoreHistory, storeKey],
  );
  const hasHydrated = useStore(store, (s) => s._internal._hasHydrated);

  // Ragbits-specific: user storage initialization
  const initializeUserStore = useCallback((userId: string) => {
    setStoreKey(`${HISTORY_STORE_KEY_BASE}-${userId}`);
  }, []);

  const value = useMemo(
    () => ({
      store,
      initializeUserStore,
    }),
    [store, initializeUserStore],
  );

  if (shouldStoreHistory && !hasHydrated) {
    return <InitializationScreen />;
  }

  return (
    <HistoryStoreContext.Provider value={value}>
      {children}
    </HistoryStoreContext.Provider>
  );
}
