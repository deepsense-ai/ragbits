import {
  ConversationIdChatResponse,
  ConversationSummaryResponse,
  FollowupMessagesChatResponse,
  StateUpdateChatResponse,
} from "@ragbits/api-client-react";
import { AfterHandler, PrimaryHandler } from "./eventHandlerRegistry";

export const handleStateUpdate: PrimaryHandler<StateUpdateChatResponse> = (
  { content },
  draft,
) => {
  draft.serverState = content;
};

export const handleConversationId: PrimaryHandler<
  ConversationIdChatResponse,
  { originalConversationId: string }
> = ({ content }, draft, ctx) => {
  const originalConversationId = ctx.conversationIdRef.current;
  draft.conversationId = content;
  // Update the ref to propagate the change
  ctx.conversationIdRef.current = content;
  return { originalConversationId };
};

export const handleAfterConversationId: AfterHandler<
  ConversationIdChatResponse,
  { originalConversationId: string }
> = (_, draft, { originalConversationId, conversationIdRef }) => {
  const oldConversation = draft.conversations[originalConversationId];

  if (!oldConversation) {
    throw new Error("Received events for non-existent conversation");
  }

  draft.conversations[conversationIdRef.current] = oldConversation;
  if (draft.currentConversation === originalConversationId) {
    draft.currentConversation = conversationIdRef.current;
  }
  delete draft.conversations[originalConversationId];
};

export const handleFollowupMessages: PrimaryHandler<
  FollowupMessagesChatResponse
> = ({ content }, draft) => {
  draft.followupMessages = content;
};

export const handleConversationSummary: PrimaryHandler<
  ConversationSummaryResponse
> = ({ content }, draft) => {
  draft.summary = content;
};
