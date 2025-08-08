import { createContext } from "react";
import { createStore } from "zustand";
import { HistoryStore } from "../../../types/history";

export const HistoryStoreContext = createContext<ReturnType<
  typeof createStore<HistoryStore, [["zustand/immer", never]]>
> | null>(null);
