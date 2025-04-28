import { ReactNode, useState } from "react";
import { ChatMessage } from "../../types/chat.ts";
import {
  ChatResponse,
  ChatResponseType,
  MessageRole,
} from "../../types/api.ts";
import { ChatHistoryContext } from "./HistoryContext.ts";
import { v4 as uuidv4 } from "uuid";

export const ChatHistoryProvider: React.FC<{ children: ReactNode }> = ({
  children,
}) => {
  const [messages, setMessages] = useState(new Map<string, ChatMessage>([]));

  const createMessage = (
    message: Partial<Omit<ChatMessage, "id" | "serverId">>,
  ): string => {
    const messageId = uuidv4();

    setMessages((state) => {
      const updatedMessages = new Map(state);

      const messageToAdd: ChatMessage = {
        id: messageId,
        role: message.role || MessageRole.USER,
        content: message.content || "",
        references: message.references || [],
        ...message,
      };

      updatedMessages.set(messageId, messageToAdd);
      return updatedMessages;
    });

    return messageId;
  };

  const updateMessage = (id: string, response: ChatResponse): void => {
    setMessages((state) => {
      const updatedMessages = new Map(state);
      const messageToUpdate = updatedMessages.get(id);

      if (!messageToUpdate) {
        throw new Error(`Message with id ${id} not found in chat history`);
      }

      if (response.type === ChatResponseType.TEXT) {
        const { content } = response;

        updatedMessages.set(id, {
          ...messageToUpdate,
          content: `${messageToUpdate.content}${content}`,
        });
      } else if (response.type === ChatResponseType.REFERENCE) {
        const { content } = response;

        updatedMessages.set(id, {
          ...messageToUpdate,
          references: [...(messageToUpdate.references || []), content],
        });
      } else if (response.type === ChatResponseType.MESSAGE_ID) {
        const { content } = response;

        updatedMessages.set(id, {
          ...messageToUpdate,
          serverId: content,
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
