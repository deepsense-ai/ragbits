import { ChatMessageProps } from "../../core/components/ChatMessage.tsx";

export interface IChatHistoryContext {
  messages: ChatMessageProps[];
  createMessage: (message: ChatMessageProps) => void;
  updateMessage: (id: string, message: string) => void;
  clearMessages: () => void;
}
