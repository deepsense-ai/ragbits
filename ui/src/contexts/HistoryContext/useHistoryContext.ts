import { useContext } from "react";
import { ChatHistoryContext, IChatHistoryContext } from "./HistoryContext";

export const useHistoryContext = (): IChatHistoryContext => {
  const context = useContext(ChatHistoryContext);
  if (!context) {
    throw new Error("useChat must be used within a ChatProvider");
  }
  return context;
};
