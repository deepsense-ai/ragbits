import { ChatResponse } from "@ragbits/api-client-react";
import { Conversation, HistoryStore } from "../../../../core/types/history";
import {
  handleAfterConversationId,
  handleConversationId,
  handleConversationSummary,
  handleFollowupMessages,
  handleStateUpdate,
} from "./nonMessageHandlers";
import {
  handleClearMessage,
  handleConfirmationRequest,
  handleError,
  handleImage,
  handleLiveUpdate,
  handleMessageId,
  handleReference,
  handleText,
  handlePlanItem,
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
  private handlers = new Map<string, unknown>();

  register<
    K extends ChatResponse["type"],
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
    K extends ChatResponse["type"],
    R extends Extract<ChatResponse, { type: K }>,
    Ctx extends object = object,
  >(type: K): HandlerEntry<R, Ctx> {
    const raw = this.handlers.get(type);
    if (!raw) {
      console.warn(`No handler registered for type: ${String(type)}`);
      console.warn(`Continuing with empty handler...`);

      return {
        handle: () => {},
        after: () => {},
      } as HandlerEntry<R, Ctx>;
    }
    return raw as HandlerEntry<R, Ctx>;
  }
}

export const ChatHandlerRegistry = new ChatResponseHandlerRegistry();
ChatHandlerRegistry.register("state_update", {
  handle: handleStateUpdate,
});
ChatHandlerRegistry.register("conversation_id", {
  handle: handleConversationId,
  after: handleAfterConversationId,
});
ChatHandlerRegistry.register("followup_messages", {
  handle: handleFollowupMessages,
});

ChatHandlerRegistry.register("text", {
  handle: handleText,
});
ChatHandlerRegistry.register("reference", {
  handle: handleReference,
});
ChatHandlerRegistry.register("message_id", {
  handle: handleMessageId,
});
ChatHandlerRegistry.register("live_update", {
  handle: handleLiveUpdate,
});
ChatHandlerRegistry.register("image", {
  handle: handleImage,
});
ChatHandlerRegistry.register("clear_message", {
  handle: handleClearMessage,
});
ChatHandlerRegistry.register("usage", {
  handle: handleUsage,
});
ChatHandlerRegistry.register("plan_item", {
  handle: handlePlanItem,
});
ChatHandlerRegistry.register("conversation_summary", {
  handle: handleConversationSummary,
});
ChatHandlerRegistry.register("confirmation_request", {
  handle: handleConfirmationRequest,
});
ChatHandlerRegistry.register("error", {
  handle: handleError,
});
