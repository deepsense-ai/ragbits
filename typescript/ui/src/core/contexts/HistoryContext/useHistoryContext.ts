import { useContext } from "react";
import { HistoryContext } from "./HistoryContext";

export const useHistoryContext = () => {
  const context = useContext(HistoryContext);
  if (!context) {
    throw new Error("useChat must be used within a ChatProvider");
  }
  return context;
};
