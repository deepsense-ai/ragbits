import {
  ChatResponse,
  LiveUpdate,
  MessageRoleType,
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
  role: MessageRoleType;
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
  lastMessageId: string | null;
  chatOptions: Record<string, unknown> | undefined;

  computed: {
    getContext: () => Record<string, unknown>;
  };

  actions: {
    clearHistory: () => void;
    sendMessage: (text: string) => void;
    stopAnswering: () => void;
    initializeChatOptions: (defaults: Record<string, unknown>) => void;
    setChatOptions: (options: Record<string, unknown>) => void;
  };

  primitives: {
    addMessage: (message: Omit<ChatMessage, "id">) => string;
    deleteMessage: (messageId: string) => void;
  };

  _internal: {
    handleResponse: (response: ChatResponse, messageId: string) => void;
  };
}
