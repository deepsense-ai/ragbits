import {
  ChatResponse,
  LiveUpdate,
  MessageRole,
  Reference,
  ServerState,
  Image,
} from "@ragbits/api-client-react";

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
  liveUpdates?: Record<string, LiveUpdate["content"]>;
  extensions?: Record<string, unknown>;
  images?: Record<string, Image["url"]>;
}

export interface ConversationHistory {
  history: Record<string, ChatMessage>;
  followupMessages: string[] | null;
  serverState: ServerState | null;
  conversationId: string | null;
  eventsLog: ChatResponse[][];
  lastMessageId: string | null;
  chatOptions: Record<string, unknown> | undefined;
}
export interface HistoryStore {
  conversations: Record<string, ConversationHistory>;
  currentConversation: string | null;
  isLoading: boolean;
  abortController: AbortController | null;

  computed: {
    getContext: () => Record<string, unknown>;
  };

  actions: {
    clearHistory: () => void;
    sendMessage: (text: string) => void;
    stopAnswering: () => void;
    /** Merge passed extensions with existing object for a given message. New values in the passed extensions
     * overwrite previous ones.
     */
    mergeExtensions: (
      messageId: string,
      extensions: Record<string, unknown>,
    ) => void;
    initializeChatOptions: (defaults: Record<string, unknown>) => void;
    setChatOptions: (options: Record<string, unknown>) => void;
    selectConversation: (conversationKey: string) => void;
    deleteConversation: (conversationKey: string) => void;
  };

  primitives: {
    addMessage: (message: Omit<ChatMessage, "id">) => string;
    deleteMessage: (messageId: string) => void;
    restore: (
      history: ConversationHistory["history"],
      followupMessages: ConversationHistory["followupMessages"],
      chatOptions: ConversationHistory["chatOptions"],
      serverState: ConversationHistory["serverState"],
      conversationId: ConversationHistory["conversationId"],
    ) => void;
    getCurrentConversation: () => ConversationHistory;
  };

  _internal: {
    handleResponse: (response: ChatResponse, messageId: string) => void;
  };
}
