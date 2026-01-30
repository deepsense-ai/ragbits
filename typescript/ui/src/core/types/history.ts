import {
  ChatResponse,
  ConfirmationRequest,
  LiveUpdate,
  MessageRole,
  Reference,
  ServerState,
  Image,
  MessageUsage,
  RagbitsClient,
  Task,
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
  usage?: Record<string, MessageUsage>;
  tasks?: Task[];
  extra?: Record<string, unknown>;
  confirmationRequests?: Record<string, ConfirmationRequest>;
  confirmationStates?: Record<
    string,
    "pending" | "confirmed" | "declined" | "skipped"
  >;
  hasConfirmationBreak?: boolean; // Flag to show visual separator after confirmations
  error?: string | null; // Error message to display in this message
}

export interface Conversation {
  history: Record<string, ChatMessage>;
  followupMessages: string[] | null;
  serverState: ServerState | null;
  conversationId: string;
  eventsLog: ChatResponse[][];
  lastMessageId: string | null;
  chatOptions: Record<string, unknown> | undefined;
  isLoading: boolean;
  abortController: AbortController | null;
  summary?: string;
}

export interface HistoryStore {
  conversations: Record<string, Conversation>;
  currentConversation: string;

  computed: {
    getContext: () => Record<string, unknown>;
  };

  actions: {
    newConversation: () => string;
    selectConversation: (conversationId: string) => void;
    deleteConversation: (conversationId: string) => void;
    sendMessage: (
      text: string,
      ragbitsClient: RagbitsClient,
      additionalContext?: Record<string, unknown>,
    ) => void;
    sendSilentConfirmation: (
      messageId: string,
      confirmationIds: string | string[],
      confirmed: boolean | Record<string, boolean>,
      ragbitsClient: RagbitsClient,
    ) => void;
    stopAnswering: () => void;
    /** Merge passed extensions with existing object for a given message. New values in the passed extensions
     * overwrite previous ones.
     */
    mergeExtensions: (
      messageId: string,
      extensions: Record<string, unknown>,
    ) => void;
    initializeChatOptions: (defaults: Record<string, unknown>) => void;
    setConversationProperties: (
      conversationKey: string,
      properties: Partial<Conversation>,
    ) => void;
  };

  primitives: {
    addMessage: (
      conversationId: string,
      message: Omit<ChatMessage, "id">,
    ) => string;
    deleteMessage: (conversationId: string, messageId: string) => void;
    restore: (
      history: Conversation["history"],
      followupMessages: Conversation["followupMessages"],
      chatOptions: Conversation["chatOptions"],
      serverState: Conversation["serverState"],
      conversationId: Conversation["conversationId"],
    ) => void;
    getCurrentConversation: () => Conversation;
    stopAnswering: (conversationId: string) => void;
  };

  _internal: {
    _hasHydrated: boolean;
    _setHasHydrated: (state: boolean) => void;
    handleResponse: (
      conversationIdRef: { current: string },
      messageId: string,
      response: ChatResponse,
    ) => void;
  };
}
