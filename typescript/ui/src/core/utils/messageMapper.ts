import { Message } from "@ragbits/api-client-react";
import { ChatMessage } from "../types/history";

/**
 * Maps the internal history state to the API message format
 */
export function mapHistoryToMessages(
  history: Record<string, ChatMessage>,
): Message[] {
  return Object.values(history).map((message) => ({
    role: message.role,
    content: message.content,
    extra: message.extra || null,
  }));
}
