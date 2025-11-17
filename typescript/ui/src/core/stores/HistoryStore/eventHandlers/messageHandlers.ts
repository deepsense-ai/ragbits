import {
  ClearMessageResponse,
  ConfirmationRequestChatResponse,
  ConfirmationStatusChatResponse,
  ImageChatResponse,
  LiveUpdateChatResponse,
  LiveUpdateType,
  MessageIdChatResponse,
  MessageUsageChatResponse,
  ReferenceChatResponse,
  TextChatResponse,
  TodoItemChatResonse,
} from "@ragbits/api-client-react";
import { PrimaryHandler } from "./eventHandlerRegistry";
import { produce } from "immer";

export const handleText: PrimaryHandler<TextChatResponse> = (
  response,
  draft,
  ctx,
) => {
  const message = draft.history[ctx.messageId];

  // Check if this is the first text after confirmation(s)
  const isAfterConfirmation =
    message.confirmationRequests &&
    message.confirmationRequests.length > 0 &&
    message.content.length === 0;

  // Add visual separator if this is the first text after confirmation
  const textToAdd = isAfterConfirmation
    ? "\n\n" + response.content
    : response.content;

  // Add text content
  message.content += textToAdd;

  // Don't auto-skip here - it's too aggressive and marks confirmations as skipped
  // even during the initial agent response. Instead, confirmations stay "pending"
  // until user clicks a button or they get marked as skipped by other means
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
  message.serverId = response.content;
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

export const handleClearMessage: PrimaryHandler<ClearMessageResponse> = (
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
  message.usage = response.content;
};

export const handleTodoItem: PrimaryHandler<TodoItemChatResonse> = (
  { content },
  draft,
  ctx,
) => {
  const message = draft.history[ctx.messageId];
  const tasks = message.tasks ?? [];
  const newTasks = produce(tasks, (tasksDraft) => {
    const taskIndex = tasksDraft.findIndex((t) => t.id === content.id);
    if (taskIndex === -1) {
      tasksDraft.push(content);
    } else {
      tasksDraft[taskIndex] = content;
    }
  });

  message.tasks = newTasks;
};

export const handleConfirmationRequest: PrimaryHandler<
  ConfirmationRequestChatResponse
> = (response, draft, ctx) => {
  const message = draft.history[ctx.messageId];

  console.log(
    "📥 Confirmation request received:",
    response.content.confirmation_id,
  );

  // Initialize arrays if they don't exist
  if (!message.confirmationRequests) {
    message.confirmationRequests = [];
  }
  if (!message.confirmationStates) {
    message.confirmationStates = {};
  }

  // Add to new array-based system
  message.confirmationRequests.push(response.content);
  message.confirmationStates[response.content.confirmation_id] = "pending";

  console.log(
    `📊 Total confirmations now: ${message.confirmationRequests.length}`,
  );
};

export const handleConfirmationStatus: PrimaryHandler<
  ConfirmationStatusChatResponse
> = (response, draft) => {
  const { confirmation_id, status } = response.content;

  // Find the message with matching confirmation_id and update its state
  Object.values(draft.history).forEach((message) => {
    if (
      message.confirmationStates &&
      confirmation_id in message.confirmationStates
    ) {
      message.confirmationStates[confirmation_id] = status as
        | "confirmed"
        | "declined";
    }
  });
};
