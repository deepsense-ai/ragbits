import { useContext } from "react";
import { useStore } from "zustand";
import { HistoryStore } from "../../types/history";
import { HistoryStoreContext } from "./HistoryStoreContext";

export const useHistoryStore = <T>(selector: (s: HistoryStore) => T): T => {
  const context = useContext(HistoryStoreContext);
  if (!context || !context.store) {
    throw new Error(
      "useHistoryStore must be used within a HistoryStoreContextProvider",
    );
  }

  return useStore(context.store, selector);
};
