import { Message } from "@ragbits/api-client-react";
import { HistoryState } from "../../types/history";

/**
 * Maps the internal history state to the API message format
 */
export function mapHistoryToMessages(history: HistoryState): Message[] {
  return Array.from(history.values()).map((message) => ({
    role: message.role,
    content: message.content,
  }));
}
