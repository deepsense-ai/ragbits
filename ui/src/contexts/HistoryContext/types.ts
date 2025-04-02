import { ChatMessageProps } from "../../core/components/ChatMessage.tsx";

export interface IChatHistoryContext {
  messages: ChatMessageProps[];
  createMessage: (message: ChatMessageProps) => string;
  updateMessage: (id: string, message: string) => void;
  clearMessages: () => void;
}
