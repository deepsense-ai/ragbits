import { ChatResponse, ChatResponseType } from "@ragbits/api-client-react";
import { Conversation, HistoryStore } from "../../../../types/history";
import {
  handleAfterConversationId,
  handleConversationId,
  handleConversationSummary,
  handleFollowupMessages,
  handleStateUpdate,
} from "./nonMessageHandlers";
import {
  handleClearMessage,
  handleImage,
  handleLiveUpdate,
  handleMessageId,
  handleReference,
  handleText,
  handleUsage,
} from "./messageHandlers";

type BaseHandlerContext = {
  conversationIdRef: { current: string };
  messageId: string;
};

export type PrimaryHandler<
  T extends ChatResponse,
  Ctx extends object = object,
> = (response: T, draft: Conversation, ctx: BaseHandlerContext) => Ctx | void;

export type AfterHandler<
  T extends ChatResponse,
  Ctx extends object = object,
> = (response: T, draft: HistoryStore, ctx: BaseHandlerContext & Ctx) => void;

export type HandlerEntry<
  T extends ChatResponse,
  Ctx extends object = object,
> = {
  handle: PrimaryHandler<T, Ctx>;
  after?: AfterHandler<T, Ctx>;
};

class ChatResponseHandlerRegistry {
  private handlers = new Map<ChatResponseType, unknown>();

  register<
    K extends ChatResponseType,
    R extends Extract<ChatResponse, { type: K }>,
    Ctx extends object = object,
  >(type: K, entry: HandlerEntry<R, Ctx>) {
    if (this.handlers.has(type)) {
      console.warn(
        `Handler for ${String(type)} already registered - overwriting.`,
      );
    }
    this.handlers.set(type, entry);
  }

  get<
    K extends ChatResponseType,
    R extends Extract<ChatResponse, { type: K }>,
    Ctx extends object = object,
  >(type: K): HandlerEntry<R, Ctx> {
    const raw = this.handlers.get(type);
    if (!raw) {
      throw new Error(`No handler registered for type: ${String(type)}`);
    }
    return raw as HandlerEntry<R, Ctx>;
  }
}

export const ChatHandlerRegistry = new ChatResponseHandlerRegistry();
ChatHandlerRegistry.register(ChatResponseType.StateUpdate, {
  handle: handleStateUpdate,
});
ChatHandlerRegistry.register(ChatResponseType.ConversationId, {
  handle: handleConversationId,
  after: handleAfterConversationId,
});
ChatHandlerRegistry.register(ChatResponseType.FollowupMessages, {
  handle: handleFollowupMessages,
});

ChatHandlerRegistry.register(ChatResponseType.Text, {
  handle: handleText,
});
ChatHandlerRegistry.register(ChatResponseType.Reference, {
  handle: handleReference,
});
ChatHandlerRegistry.register(ChatResponseType.MessageId, {
  handle: handleMessageId,
});
ChatHandlerRegistry.register(ChatResponseType.LiveUpdate, {
  handle: handleLiveUpdate,
});
ChatHandlerRegistry.register(ChatResponseType.Image, {
  handle: handleImage,
});
ChatHandlerRegistry.register(ChatResponseType.ClearMessage, {
  handle: handleClearMessage,
});
ChatHandlerRegistry.register(ChatResponseType.Usage, {
  handle: handleUsage,
});
ChatHandlerRegistry.register(ChatResponseType.ConversationSummary, {
  handle: handleConversationSummary,
});
