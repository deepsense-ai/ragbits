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

  const createMessage = (message: ChatMessageProps): void =>
    setMessages((state) => [...state, message]);

  const updateMessage = (id: string, data: string): void =>
    setMessages((state) => {
      const updatedMessages = [...state];

      const index = updatedMessages.findIndex((msg) => msg.id === id);
      if (index !== -1) {
        updatedMessages[index] = {
          ...updatedMessages[index],
          message: updatedMessages[index].message + data,
        };
      }

      return updatedMessages;
    });

  const clearMessages = (): void => {
    setMessages([]);
  };

  return (
    <ChatHistoryContext.Provider
      value={{ messages, createMessage, updateMessage, clearMessages }}
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
