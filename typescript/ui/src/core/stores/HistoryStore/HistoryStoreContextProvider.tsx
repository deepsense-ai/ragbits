import { PropsWithChildren, useMemo, useState } from "react";
import { createStore, useStore } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import { HistoryStoreContext } from "./HistoryStoreContext";
import { Conversation } from "../../types/history";
import InitializationScreen from "../../components/InitializationScreen";
import { createHistoryStore } from "../../../ragbits/stores/HistoryStore/historyStore";
import { IndexedDBStorage } from "../../../ragbits/stores/HistoryStore/indexedDBStorage";

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

  // Manually set _hasHydrated when we don't use any storage
  const store = createStore(createHistoryStore);
  store.getState()._internal._setHasHydrated(true);

  return store;
}

export default function HistoryStoreContextProvider({
  children,
  shouldStoreHistory,
}: PropsWithChildren<HistoryStoreContextProviderProps>) {
  const [storeKey, _setStoreKey] = useState(HISTORY_STORE_KEY_BASE);
  const store = useMemo(
    () => initializeStore(shouldStoreHistory, storeKey),
    [shouldStoreHistory, storeKey],
  );
  const hasHydrated = useStore(store, (s) => s._internal._hasHydrated);

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

  if (shouldStoreHistory && !hasHydrated) {
    return <InitializationScreen />;
  }

  return (
    <HistoryStoreContext.Provider value={value}>
      {children}
    </HistoryStoreContext.Provider>
  );
}
