import {
  TypedChatResponse as ChatResponse,
  LiveUpdate,
  MessageRole,
  Reference,
} from "@ragbits/api-client-react";

export type HistoryState = Map<string, ChatMessage>;

export type UnsubscribeFn = (() => void) | null;

export interface ChatMessage {
  id: string;
  /**
   * Bot messages would have this set to the server ID (sent in the first event, with type of `message_id`)
   */
  serverId?: string;
  role: MessageRole;
  content: string;
  references?: Reference[];
  liveUpdates?: Map<string, LiveUpdate["content"]>;
}

export interface HistoryContext {
  history: ChatMessage[];
  followupMessages: string[] | null;
  isLoading: boolean;
  /**
   * Sends a message to the chat window with animations and delayed rendering.
   */
  sendMessage: (text: string, options?: Record<string, unknown>) => void;
  /**
   * Primitive used for adding a message to the history and get its ID.
   */
  addMessage: (message: Omit<ChatMessage, "id">) => string;
  /**
   * Primitive used for updating a message in the history based on the passed response.
   */
  handleResponse: (chatResponse: ChatResponse, messageId: string) => void;
  clearHistory: () => void;
  stopAnswering: () => void;
}
