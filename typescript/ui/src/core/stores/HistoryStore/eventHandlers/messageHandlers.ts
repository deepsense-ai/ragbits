import {
  ClearMessageChatResponse,
  ConfirmationRequestChatResponse,
  ErrorChatResponse,
  ImageChatResponse,
  LiveUpdateChatResponse,
  LiveUpdateType,
  MessageIdChatResponse,
  MessageUsageChatResponse,
  ReferenceChatResponse,
  TextChatResponse,
} from "@ragbits/api-client-react";
import { PrimaryHandler } from "./eventHandlerRegistry";
import { produce } from "immer";

export const handleText: PrimaryHandler<TextChatResponse> = (
  response,
  draft,
  ctx,
) => {
  const message = draft.history[ctx.messageId];
  message.content += response.content.text;
};

export const handleReference: PrimaryHandler<ReferenceChatResponse> = (
  response,
  draft,
  ctx,
) => {
  const message = draft.history[ctx.messageId];
  message.references = [...(message.references ?? []), response.content];
};

export const handleMessageId: PrimaryHandler<MessageIdChatResponse> = (
  response,
  draft,
  ctx,
) => {
  const message = draft.history[ctx.messageId];
  message.serverId = response.content.message_id;
};

export const handleLiveUpdate: PrimaryHandler<LiveUpdateChatResponse> = (
  response,
  draft,
  ctx,
) => {
  const message = draft.history[ctx.messageId];

  const { update_id, content, type } = response.content;
  const liveUpdates = produce(message.liveUpdates ?? {}, (draft) => {
    if (type === LiveUpdateType.Start && update_id in draft) {
      console.error(
        `Got duplicate start event for update_id: ${update_id}. Ignoring the event.`,
      );
    }

    draft[update_id] = content;
  });
  message.liveUpdates = liveUpdates;
};

export const handleImage: PrimaryHandler<ImageChatResponse> = (
  response,
  draft,
  ctx,
) => {
  const message = draft.history[ctx.messageId];
  const image = response.content;
  message.images = produce(message.images ?? {}, (draft) => {
    if (draft[image.id]) {
      console.error(
        `Got duplicate image event for image_id: ${image.id}. Ignoring the event.`,
      );
    }

    draft[image.id] = image.url;
  });
};

export const handleClearMessage: PrimaryHandler<ClearMessageChatResponse> = (
  _,
  draft,
  ctx,
) => {
  const message = draft.history[ctx.messageId];
  draft.history[ctx.messageId] = {
    id: message.id,
    role: message.role,
    content: "",
  };
};

export const handleUsage: PrimaryHandler<MessageUsageChatResponse> = (
  response,
  draft,
  ctx,
) => {
  const message = draft.history[ctx.messageId];
  message.usage = response.content.usage;
};

export const handleTodoItem: PrimaryHandler<TodoItemChatResonse> = (
  { content },
  draft,
  ctx,
) => {
  const message = draft.history[ctx.messageId];
  const tasks = message.tasks ?? [];
  const task = content.task;
  const newTasks = produce(tasks, (tasksDraft) => {
    const taskIndex = tasksDraft.findIndex((t) => t.id === task.id);
    if (taskIndex === -1) {
      tasksDraft.push(task);
    } else {
      tasksDraft[taskIndex] = task;
    }
  });

  message.tasks = newTasks;
};

export const handleConfirmationRequest: PrimaryHandler<
  ConfirmationRequestChatResponse
> = (response, draft, ctx) => {
  const message = draft.history[ctx.messageId];

  const confirmationId = response.content.confirmation_request.confirmation_id;

  // Initialize Records if they don't exist
  if (!message.confirmationRequests) {
    message.confirmationRequests = {};
  }
  if (!message.confirmationStates) {
    message.confirmationStates = {};
  }

  // Check if this confirmation already exists
  if (confirmationId in message.confirmationRequests) {
    return;
  }

  // Add to Record-based system (prevents duplicates by design)
  message.confirmationRequests[confirmationId] =
    response.content.confirmation_request;
  message.confirmationStates[confirmationId] = "pending";
};

export const handleError: PrimaryHandler<ErrorChatResponse> = (
  response,
  draft,
  ctx,
) => {
  const message = draft.history[ctx.messageId];
  message.error = response.content.message;
};
