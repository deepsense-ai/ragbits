import { IChatHistoryContext } from "./types.ts";
import { createContext, ReactNode, useContext, useState } from "react";
import { ChatMessageProps } from "../../core/components/ChatMessage.tsx";
import { v4 as uuidv4 } from "uuid";

const ChatHistoryContext = createContext<IChatHistoryContext | undefined>(
  undefined,
);

export const ChatHistoryProvider: React.FC<{ children: ReactNode }> = ({
  children,
}) => {
  const [messages, setMessages] = useState(
    new Map<string, ChatMessageProps>([]),
  );

  const createMessage = (message: ChatMessageProps): string => {
    const id = uuidv4();

    setMessages((state) => {
      const updatedMessages = new Map(state);
      updatedMessages.set(id, { ...message });

      return updatedMessages;
    });

    return id;
  };

  const updateMessage = (id: string, message: string): void => {
    setMessages((state) => {
      const updatedMessages = new Map(state);
      if (updatedMessages.has(id)) {
        // TODO: We should handle updates for different message types
        // TODO: Throw error if message is not found, this should not happen and should be handled explicitly
        const existingMessage = updatedMessages.get(id)!;
        updatedMessages.set(id, {
          ...existingMessage,
          message: `${existingMessage.message}${message}`,
        });
      }
      return updatedMessages;
    });
  };

  const clearMessages = (): void => {
    setMessages(new Map([]));
  };

  return (
    <ChatHistoryContext.Provider
      value={{
        messages: Array.from(messages.values()),
        createMessage,
        updateMessage,
        clearMessages,
      }}
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
