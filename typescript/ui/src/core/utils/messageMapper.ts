import { Message } from "ragbits-api-client-react";
import { ChatMessage } from "../../types/history";

/**
 * Maps the internal history messages to the API message format
 */
export function mapHistoryToMessages(messages: ChatMessage[]): Message[] {
  return messages.map((message) => ({
    role: message.role,
    content: message.content,
    id: message.serverId,
  }));
}
