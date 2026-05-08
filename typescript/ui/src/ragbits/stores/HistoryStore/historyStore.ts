import {
  ChatRequest,
  ChatResponse,
  HttpError,
  MessageRole,
  RagbitsClient,
} from "@ragbits/api-client-react";
import {
  ChatMessage,
  Conversation,
  HistoryStore,
} from "../../../core/types/history";
import { immer } from "zustand/middleware/immer";
import { omitBy } from "lodash";
import { ChatHandlerRegistry } from "./eventHandlers/eventHandlerRegistry";
import { TextChatResponse } from "@ragbits/api-client-react";

import { mapHistoryToMessages } from "../../../core/utils/messageMapper";
import {
  initialHistoryValues,
  isTemporaryConversation,
  updateConversation,
  initialConversationValues,
} from "../../../core/stores/HistoryStore/utils";
import { v4 as uuidv4 } from "uuid";

export const FLUSH_INTERVAL_MS = 100;

type BufferedEvent = {
  response: ChatResponse;
  conversationIdRef: { current: string };
  messageId: string;
};

/**
 * Queues incoming SSE events and flushes them in batch at a throttled interval.
 * This decouples the SSE data stream from React rendering, preventing GC
 * thrashing and renderer overload during high-throughput streams.
 */
export class EventBuffer {
  private queue: BufferedEvent[] = [];
  private timerId: ReturnType<typeof setTimeout> | null = null;
  private flushFn: (events: BufferedEvent[]) => void;
  private intervalMs: number;

  constructor(
    flushFn: (events: BufferedEvent[]) => void,
    intervalMs: number = FLUSH_INTERVAL_MS,
  ) {
    this.flushFn = flushFn;
    this.intervalMs = intervalMs;
  }

  enqueue(
    response: ChatResponse,
    conversationIdRef: { current: string },
    messageId: string,
  ): void {
    this.queue.push({ response, conversationIdRef, messageId });

    if (this.timerId === null) {
      this.timerId = setTimeout(() => {
        this.timerId = null;
        this.flush();
      }, this.intervalMs);
    }
  }

  flush(): void {
    if (this.queue.length === 0) return;

    const events = this.queue;
    this.queue = [];

    if (this.timerId !== null) {
      clearTimeout(this.timerId);
      this.timerId = null;
    }

    this.flushFn(events);
  }

  dispose(): void {
    if (this.timerId !== null) {
      clearTimeout(this.timerId);
      this.timerId = null;
    }
    this.queue = [];
  }
}

export const createHistoryStore = immer<HistoryStore>((set, get) => ({
  ...initialHistoryValues(),
  computed: {
    getContext: () => {
      const {
        primitives: { getCurrentConversation },
      } = get();
      const conversation = getCurrentConversation();
      const { serverState, conversationId, chatOptions } = conversation;
      return {
        ...(serverState ?? {}),
        ...(conversationId &&
        !isTemporaryConversation(conversation.conversationId)
          ? { conversation_id: conversationId }
          : {}),
        ...(chatOptions ? { user_settings: chatOptions } : {}),
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      };
    },
  },
  _internal: {
    _hasHydrated: false,
    _setHasHydrated: (state) => {
      set((draft) => {
        draft._internal._hasHydrated = state;
      });
    },
    handleResponse: (conversationIdRef, messageId, response) => {
      let additionalContext: object | void = undefined;
      const handlers = ChatHandlerRegistry.get(response.type);

      set(
        updateConversation(conversationIdRef.current, (draft) => {
          const message = draft.history[messageId];
          if (!message)
            throw new Error(`Message ID ${messageId} not found in history`);

          additionalContext = handlers.handle(response, draft, {
            conversationIdRef,
            messageId,
          });
        }),
      );

      set((draft) => {
        handlers.after?.(response, draft, {
          conversationIdRef,
          messageId,
          ...additionalContext,
        });
      });

      set(
        updateConversation(conversationIdRef.current, (draft) => {
          draft.eventsLog[draft.eventsLog.length - 1].push(response);
        }),
      );
    },
  },

  primitives: {
    getCurrentConversation: () => {
      const { currentConversation, conversations } = get();
      const conversation = conversations[currentConversation];

      if (!conversation) {
        throw new Error("Tried to get conversation that doesn't exist.");
      }

      return conversation;
    },

    addMessage: (conversationId, message) => {
      const id = uuidv4();
      const newMessage: ChatMessage = { ...message, id };
      set(
        updateConversation(conversationId, (draft) => {
          draft.followupMessages = null;
          draft.lastMessageId = id;
          draft.history[id] = newMessage;
        }),
      );
      return id;
    },

    deleteMessage: (conversationId, messageId) => {
      set(
        updateConversation(conversationId, (draft) => {
          const { history } = draft;
          const messageIds = Object.keys(history);

          if (messageIds.at(-1) === messageId) {
            draft.lastMessageId = messageIds.at(-2) ?? null;
          }

          delete draft.history[messageId];
        }),
      );
    },

    stopAnswering: (conversationId: string) => {
      const conversation = get().conversations[conversationId];

      if (!conversation) {
        throw new Error(
          "Tried to stop answering for conversation that doesn't exist",
        );
      }

      conversation.abortController?.abort();
      set(
        updateConversation(conversationId, (draft) => {
          draft.abortController = null;
          draft.isLoading = false;
        }),
      );
    },
  },

  actions: {
    selectConversation: (conversationId) => {
      set((draft) => {
        if (draft.currentConversation === conversationId) {
          return;
        }
        const conversation = draft.conversations[conversationId];
        if (!conversation) {
          throw new Error(
            `Tried to select conversation that doesn't exist, id: ${conversationId}`,
          );
        }

        draft.currentConversation = conversationId;
      });
    },
    deleteConversation: (conversationId, ragbitsClient) => {
      const {
        actions: { newConversation },
        primitives: { stopAnswering },
        currentConversation,
        conversations,
      } = get();
      stopAnswering(conversationId);

      const conv = conversations[conversationId];
      const isPersisted = !isTemporaryConversation(conversationId);
      if (isPersisted && ragbitsClient) {
        const serverCall = conv?.isShared
          ? ragbitsClient.makeRequest("/api/shared/:conversationId", {
              method: "DELETE",
              pathParams: { conversationId },
            })
          : ragbitsClient.makeRequest("/api/conversations/:conversationId", {
              method: "DELETE",
              pathParams: { conversationId },
            });
        serverCall.catch((err) => {
          // 404 means the row is already gone server-side (deleted in another
          // tab, share revoked, stale localStorage entry). Local removal is
          // already happening below, so treat it as success.
          if (err instanceof HttpError && err.status === 404) return;
          console.error(`Failed to delete conversation ${conversationId}`, err);
        });
      }

      set((draft) => {
        delete draft.conversations[conversationId];
      });

      if (conversationId === currentConversation) {
        return newConversation();
      }
    },
    mergeExtensions: (messageId, extensions) => {
      const { currentConversation } = get();
      set(
        updateConversation(currentConversation, (draft) => {
          if (!(messageId in draft.history)) {
            throw new Error(
              "Attempted to set extensions for a message that does not exist.",
            );
          }

          const existingMessage = draft.history[messageId];
          existingMessage.extensions = {
            ...existingMessage.extensions,
            ...extensions,
          };
          draft.history[messageId] = existingMessage;
        }),
      );
    },

    initializeChatOptions: (defaultOptions) => {
      const { currentConversation } = get();
      set(
        updateConversation(currentConversation, (draft) => {
          const currentOptions = draft.chatOptions ?? {};
          Object.keys(currentOptions).forEach((key) => {
            if (!(key in defaultOptions)) {
              delete currentOptions[key];
            }
          });

          Object.keys(defaultOptions).forEach((key) => {
            if (!(key in currentOptions)) {
              currentOptions[key] = defaultOptions[key];
            }
          });

          draft.chatOptions = currentOptions;
        }),
      );
    },
    setConversationProperties: (conversationKey, properties) => {
      set(
        updateConversation(conversationKey, (draft) => {
          Object.assign(draft, properties);
        }),
      );
    },

    stopAnswering: () => {
      const {
        currentConversation,
        primitives: { stopAnswering },
      } = get();
      stopAnswering(currentConversation);
    },

    newConversation: () => {
      const newConversation = initialConversationValues();
      set((draft) => {
        draft.conversations[newConversation.conversationId] = newConversation;
        draft.currentConversation = newConversation.conversationId;

        // Cleanup unused temporary conversations
        draft.conversations = omitBy(
          draft.conversations,
          (c) =>
            isTemporaryConversation(c.conversationId) &&
            c.conversationId !== draft.currentConversation,
        );
      });

      return newConversation.conversationId;
    },

    loadServerConversations: async (ragbitsClient: RagbitsClient) => {
      let metas;
      try {
        metas = await ragbitsClient.makeRequest("/api/conversations", {
          method: "GET",
        });
      } catch (err) {
        console.error("Failed to load server conversations", err);
        return;
      }
      set((draft: HistoryStore) => {
        const serverIds = new Set((metas ?? []).map((m) => m.conversation_id));

        // Drop persisted conversations that no longer exist on the server.
        // The server is authoritative for any non-temp conversation: if it
        // didn't return it, the conversation was deleted, the share was
        // revoked, or it was dismissed. We keep the currently selected
        // conversation around so a redirect (handled by ConversationGuard)
        // can resolve cleanly instead of crashing on a missing entry.
        for (const id of Object.keys(draft.conversations)) {
          if (
            !isTemporaryConversation(id) &&
            id !== draft.currentConversation &&
            !serverIds.has(id)
          ) {
            delete draft.conversations[id];
          }
        }

        for (const meta of metas ?? []) {
          const existing = draft.conversations[meta.conversation_id];
          if (existing) {
            if (meta.is_shared) {
              existing.isShared = true;
              existing.sharedBy = meta.shared_by ?? undefined;
            }
            if (meta.summary && !existing.summary) {
              existing.summary = meta.summary;
            }
          } else {
            draft.conversations[meta.conversation_id] = {
              ...initialConversationValues(),
              conversationId: meta.conversation_id,
              summary: meta.summary ?? undefined,
              isShared: meta.is_shared ?? false,
              sharedBy: meta.shared_by ?? undefined,
              isServerOnly: true,
            };
          }
        }
      });
    },

    loadSharedConversation: async (
      conversationId: string,
      ragbitsClient: RagbitsClient,
    ) => {
      let detail;
      try {
        detail = await ragbitsClient.makeRequest(
          "/api/conversations/:conversationId",
          {
            method: "GET",
            pathParams: { conversationId },
          },
        );
      } catch (err) {
        // 404 just means the user has no access to this conversation (never
        // existed, share revoked, deleted) — that's an expected outcome of
        // following a stale link, not a bug worth logging.
        if (!(err instanceof HttpError && err.status === 404)) {
          console.error(
            `Failed to load shared conversation ${conversationId}`,
            err,
          );
        }
        return false;
      }
      if (!detail) return false;

      const history: Record<string, ChatMessage> = {};
      let lastId: string | null = null;
      for (const interaction of detail.messages) {
        const userMsgId = interaction.message_id ?? uuidv4();
        history[userMsgId] = {
          id: userMsgId,
          role: MessageRole.User,
          content: interaction.message,
        };
        const botMsgId = `${userMsgId}-response`;
        history[botMsgId] = {
          id: botMsgId,
          role: MessageRole.Assistant,
          content: interaction.response,
        };
        lastId = botMsgId;
      }

      set((draft: HistoryStore) => {
        const existing = draft.conversations[detail.conversation_id];
        const conv: Conversation = {
          ...initialConversationValues(),
          conversationId: detail.conversation_id,
          summary: existing?.summary,
          isShared: detail.is_shared ?? false,
          sharedBy: detail.shared_by ?? undefined,
          isServerOnly: false,
          history,
          lastMessageId: lastId,
        };
        draft.conversations[detail.conversation_id] = conv;
      });
      return true;
    },

    sendMessage: (text, ragbitsClient, additionalContext) => {
      const {
        _internal: { handleResponse },
        primitives: { addMessage, getCurrentConversation, stopAnswering },
        computed: { getContext },
      } = get();

      const { history, conversationId, isShared } = getCurrentConversation();

      if (isShared) return;

      addMessage(conversationId, {
        role: MessageRole.User,
        content: text,
      });

      // Add empty assistant message that will be filled with the response
      const assistantResponseId = addMessage(conversationId, {
        role: MessageRole.Assistant,
        content: "",
      });

      const chatRequest: ChatRequest = {
        message: text,
        history: mapHistoryToMessages(history),
        context: { ...getContext(), ...additionalContext },
      };

      // Add new entry for events
      set(
        updateConversation(conversationId, (draft) => {
          draft.eventsLog.push([]);
        }),
      );

      const abortController = new AbortController();
      const conversationIdRef = { current: conversationId };

      set(
        updateConversation(conversationId, (draft) => {
          draft.abortController = abortController;
          draft.isLoading = true;
        }),
      );

      const buffer = new EventBuffer((events) => {
        // Separate text events (hot path) from non-text events (rare)
        const textEvents: TextChatResponse[] = [];
        const otherEvents: BufferedEvent[] = [];
        for (const event of events) {
          if (event.response.type === "text") {
            textEvents.push(event.response as TextChatResponse);
          } else {
            otherEvents.push(event);
          }
        }

        // Apply all text chunks in a SINGLE immer produce call
        if (textEvents.length > 0) {
          // Build batch string OUTSIDE immer to avoid V8 cons-string chains
          // and repeated Proxy setter calls
          const batchText = textEvents.map((t) => t.content.text).join("");
          set(
            updateConversation(conversationIdRef.current, (draft) => {
              const message = draft.history[assistantResponseId];
              message.content = message.content + batchText;
            }),
          );
        }

        // Non-text events go through the full handler (rare, won't cause OOM)
        for (const event of otherEvents) {
          handleResponse(
            event.conversationIdRef,
            event.messageId,
            event.response,
          );
        }
      });

      ragbitsClient.makeStreamRequest(
        "/api/chat",
        chatRequest,
        {
          onMessage: (response: ChatResponse) =>
            buffer.enqueue(response, conversationIdRef, assistantResponseId),
          onError: (error: Error) => {
            buffer.flush();
            buffer.dispose();
            handleResponse(conversationIdRef, assistantResponseId, {
              type: "text",
              content: { text: error.message },
            });
            stopAnswering(conversationIdRef.current);
          },
          onClose: () => {
            buffer.flush();
            buffer.dispose();
            stopAnswering(conversationIdRef.current);
          },
        },
        abortController.signal,
      );
    },

    sendSilentConfirmation: (
      messageId: string,
      confirmationIds: string | string[],
      confirmed: boolean | Record<string, boolean>,
      ragbitsClient,
    ) => {
      const {
        _internal: { handleResponse },
        primitives: { getCurrentConversation, stopAnswering },
        computed: { getContext },
      } = get();

      const { history, conversationId } = getCurrentConversation();

      // Normalize inputs to arrays
      const idsArray = Array.isArray(confirmationIds)
        ? confirmationIds
        : [confirmationIds];
      const decisionsMap =
        typeof confirmed === "boolean"
          ? idsArray.reduce(
              (acc, id) => ({ ...acc, [id]: confirmed }),
              {} as Record<string, boolean>,
            )
          : confirmed;

      // Update confirmation states immediately in the UI
      set(
        updateConversation(conversationId, (draft) => {
          const message = draft.history[messageId];
          if (message && message.confirmationStates) {
            idsArray.forEach((id) => {
              if (id in message.confirmationStates!) {
                message.confirmationStates![id] = decisionsMap[id]
                  ? "confirmed"
                  : "declined";
              }
            });

            // Set flag to show visual separator after confirmations
            message.hasConfirmationBreak = true;

            // Clear the "⏳ Awaiting user confirmation" live update
            // before the agent re-runs and sends new updates
            message.liveUpdates = undefined;
          }
        }),
      );

      // Reuse the same message for the response instead of creating a new one
      const assistantResponseId = messageId;

      // Prepare the chat request with tool_confirmations context
      // Build the tool_confirmations array from all decisions
      const tool_confirmations = idsArray.map((id) => ({
        confirmation_id: id,
        confirmed: decisionsMap[id],
      }));

      // Use empty message since this is a silent confirmation
      const chatRequest: ChatRequest = {
        message: "",
        history: mapHistoryToMessages(history),
        context: {
          ...getContext(),
          tool_confirmations,
        },
      };

      // Add new entry for events
      set(
        updateConversation(conversationId, (draft) => {
          draft.eventsLog.push([]);
        }),
      );

      const abortController = new AbortController();
      const conversationIdRef = { current: conversationId };

      set(
        updateConversation(conversationId, (draft) => {
          draft.abortController = abortController;
          draft.isLoading = true;
        }),
      );

      // Use the same assistant message for the response
      const buffer = new EventBuffer((events) => {
        // Separate text events (hot path) from non-text events (rare)
        const textEvents: TextChatResponse[] = [];
        const otherEvents: BufferedEvent[] = [];
        for (const event of events) {
          if (event.response.type === "text") {
            textEvents.push(event.response as TextChatResponse);
          } else {
            otherEvents.push(event);
          }
        }

        // Apply all text chunks in a SINGLE immer produce call
        if (textEvents.length > 0) {
          // Build batch string OUTSIDE immer to avoid V8 cons-string chains
          // and repeated Proxy setter calls
          const batchText = textEvents.map((t) => t.content.text).join("");
          set(
            updateConversation(conversationIdRef.current, (draft) => {
              const message = draft.history[assistantResponseId];
              message.content = message.content + batchText;
            }),
          );
        }

        // Non-text events go through the full handler (rare, won't cause OOM)
        for (const event of otherEvents) {
          handleResponse(
            event.conversationIdRef,
            event.messageId,
            event.response,
          );
        }
      });

      ragbitsClient.makeStreamRequest(
        "/api/chat",
        chatRequest,
        {
          onMessage: (response: ChatResponse) =>
            buffer.enqueue(response, conversationIdRef, assistantResponseId),
          onError: (error: Error) => {
            buffer.flush();
            buffer.dispose();
            handleResponse(conversationIdRef, assistantResponseId, {
              type: "text",
              content: { text: error.message },
            });
            stopAnswering(conversationIdRef.current);
          },
          onClose: () => {
            buffer.flush();
            buffer.dispose();
            stopAnswering(conversationIdRef.current);
          },
        },
        abortController.signal,
      );
    },
  },
}));
