import { ChatMessageProps } from "../../core/components/ChatMessage.tsx";

export interface IChatHistoryContext {
  messages: Map<string, ChatMessageProps>;
  createMessage: (message: ChatMessageProps) => string;
  updateMessage: (id: string, message: string) => void;
  clearMessages: () => void;
}
