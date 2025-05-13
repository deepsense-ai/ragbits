import {
  ChatResponse,
  ChatResponseType,
  Message,
  MessageRole,
} from "../../types/api";
import { HistoryContext } from "../../types/history";

export const buildApiUrl = (path: string) => {
  const devUrl = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";
  const baseUrl = import.meta.env.DEV ? devUrl : "";

  // Ensure that baseUrl doesn't end with a slash
  if (baseUrl.endsWith("/")) {
    return `${baseUrl.slice(0, -1)}${path}`;
  }

  return `${baseUrl}${path}`;
};

export function mapHistoryToMessages(
  history: HistoryContext["history"],
): Message[] {
  return (
    history
      // Note: Exclude system messages as they are relevant only in the UI
      .filter((message) => message.role !== MessageRole.SYSTEM)
      .map((message) => ({
        role: message.role,
        content: message.content,
      }))
  );
}

export function isChatResponse(data: unknown): data is ChatResponse {
  return (
    typeof data === "object" &&
    data !== null &&
    "type" in data &&
    "content" in data &&
    Object.values(ChatResponseType).includes(data.type as ChatResponseType) &&
    (typeof data.content === "object" || typeof data.content === "string")
  );
}
