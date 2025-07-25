import { PropsWithChildren, useState } from "react";
import { createStore } from "zustand";
import { createHistoryStore } from "./historyStore";
import { createJSONStorage, persist } from "zustand/middleware";
import { IndexedDBStorage } from "./indexedDBStorage";
import { HistoryStoreContext } from "./HistoryStoreContext";

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
