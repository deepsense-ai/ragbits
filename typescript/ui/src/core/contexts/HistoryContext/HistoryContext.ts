import { createContext } from "react";
import { HistoryContext as IHistoryContext } from "../../../types/history";

export const HistoryContext = createContext<IHistoryContext | undefined>(
  undefined,
);
