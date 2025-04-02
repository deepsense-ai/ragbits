import { ChatMessageProps } from "../../core/components/ChatMessage.tsx";

export interface IChatHistoryContext {
  messages: ChatMessageProps[];
  addMessage: (message: ChatMessageProps) => void;
  clearMessages: () => void;
}
