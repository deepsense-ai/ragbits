import {
  ChatResponse,
  LiveUpdate,
  MessageRole,
  Reference,
  ServerState,
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

export interface HistoryStore {
  history: Map<string, ChatMessage>;
  followupMessages: string[] | null;
  serverState: ServerState | null;
  conversationId: string | null;
  eventsLog: ChatResponse[][];
  isLoading: boolean;
  abortController: AbortController | null;
  context: Record<string, unknown> | undefined;
  lastMessageId: string | null;

  actions: {
    clearHistory: () => void;
    sendMessage: (text: string, options?: Record<string, unknown>) => void;
    stopAnswering: () => void;
  };

  primitives: {
    addMessage: (message: Omit<ChatMessage, "id">) => string;
    deleteMessage: (messageId: string) => void;
  };

  _internal: {
    handleResponse: (response: ChatResponse, messageId: string) => void;
  };
}
