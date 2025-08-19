import { PropsWithChildren, useMemo, useState } from "react";
import { createStore } from "zustand";
import { createHistoryStore } from "./historyStore";
import { createJSONStorage, persist } from "zustand/middleware";
import { IndexedDBStorage } from "./indexedDBStorage";
import { HistoryStoreContext } from "./HistoryStoreContext";
import { transform } from "lodash";
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
          const { conversations, currentConversation } = currentState;
          const finalState = {
            ...currentState,
            ...(persistedState ?? {}),
          };

          // When loading the state, we need to reset the `isLoading` and `abortController` properties,
          // since any information about the current stream is lost when the app is closed or reloaded.
          finalState.conversations = transform<
            Conversation,
            Record<string, Conversation>
          >(
            finalState.conversations,
            (res, c) => {
              // Ignore old conversations with `null` as key
              if (c.conversationId === null) {
                return;
              }

              const newKey = c.conversationId;
              const newValue = {
                ...c,
                isLoading: false,
                abortController: null,
              };
              res[newKey] = newValue;
            },
            {},
          );
          // This ensures that we always start with empty conversation
          finalState.conversations[currentConversation] =
            conversations[currentConversation];
          finalState.currentConversation = currentConversation;

          return finalState;
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
