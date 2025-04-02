import { IChatHistoryContext } from "./types.ts";
import { createContext, ReactNode, useContext, useState } from "react";
import { ChatMessageProps } from "../../core/components/ChatMessage.tsx";

const ChatHistoryContext = createContext<IChatHistoryContext | undefined>(
  undefined,
);

export const ChatHistoryProvider: React.FC<{ children: ReactNode }> = ({
  children,
}) => {
  const [messages, setMessages] = useState<ChatMessageProps[]>([]);

  const addMessage = (message: ChatMessageProps) => {
    setMessages((prevMessages) => [...prevMessages, message]);
  };

  const clearMessages = () => {
    setMessages([]);
  };

  return (
    <ChatHistoryContext.Provider
      value={{ messages, addMessage, clearMessages }}
    >
      {children}
    </ChatHistoryContext.Provider>
  );
};

export const useChatHistory = (): IChatHistoryContext => {
  const context = useContext(ChatHistoryContext);
  if (!context) {
    throw new Error("useChat must be used within a ChatProvider");
  }
  return context;
};
