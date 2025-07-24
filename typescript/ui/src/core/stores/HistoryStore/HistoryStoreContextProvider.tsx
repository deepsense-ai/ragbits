import { PropsWithChildren, useState } from "react";
import { createStore } from "zustand";
import { createHistoryStore } from "./historyStore";
import { createJSONStorage, persist } from "zustand/middleware";
import { IndexedDBStorage } from "./indexedDBStorage";
import { HistoryStoreContext } from "./HistoryStoreContext";
import { transform } from "lodash";
import { Conversation } from "../../../types/history";

interface HistoryStoreContextProviderProps {
  shouldStoreHistory: boolean;
}

export function HistoryStoreContextProvider({
  children,
  shouldStoreHistory,
}: PropsWithChildren<HistoryStoreContextProviderProps>) {
  const [store] = useState(() =>
    shouldStoreHistory
      ? createStore(
          persist(
            createHistoryStore,

            {
              name: "ragbits-history-store",
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
            },
          ),
        )
      : createStore(createHistoryStore),
  );

  return (
    <HistoryStoreContext.Provider value={store}>
      {children}
    </HistoryStoreContext.Provider>
  );
}
