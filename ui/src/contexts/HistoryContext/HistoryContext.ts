import { createContext } from "react";
import { ChatResponse } from "../../types/api";
import { ChatMessage } from "../../types/chat";

export interface IChatHistoryContext {
  messages: ChatMessage[];
  createMessage: (message: Partial<ChatMessage>) => string;
  // TODO: We can add additional argument that would allow custom modification
  // of the message before updating
  // TODO: We can add flag to allow replacing the message instead of appending
  updateMessage: (id: string, message: ChatResponse) => void;
  clearMessages: () => void;
}

export const ChatHistoryContext = createContext<
  IChatHistoryContext | undefined
>(undefined);
