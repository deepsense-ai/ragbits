import {
  ClearMessageResponse,
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
  message.content += response.content;
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
