import { Conversation, HistoryStore } from "../../types/history";
import { v4 as uuidv4 } from "uuid";

export const TEMPORARY_CONVERSATION_TAG = "temp-";

export const isTemporaryConversation = (conversationId: string) => {
  return conversationId.startsWith(TEMPORARY_CONVERSATION_TAG);
};

export const updateConversation = (
  conversationId: string,
  mutator: (draft: Conversation) => void,
) => {
  return (draft: HistoryStore) => {
    const conversation = draft.conversations[conversationId];
    if (!conversation) {
      throw new Error(
        `Conversation with ID '${conversationId}' does not exist`,
      );
    }

    mutator(conversation);
  };
};

export const getTemporaryConversationId = () =>
  `${TEMPORARY_CONVERSATION_TAG}${uuidv4()}`;

export const initialConversationValues = () => ({
  history: {},
  followupMessages: null,
  serverState: null,
  conversationId: getTemporaryConversationId(),
  eventsLog: [],
  lastMessageId: null,
  context: undefined,
  chatOptions: undefined,
  isLoading: false,
  abortController: null,
});

export const initialHistoryValues = () => {
  // Always initialize with empty conversation
  const startingConversation = initialConversationValues();
  return {
    conversations: {
      [startingConversation.conversationId]: startingConversation,
    },
    currentConversation: startingConversation.conversationId,
  };
};
