import { Button } from "@heroui/react";
import { Icon } from "@iconify/react";
import {
  getConversationKey,
  useHistoryActions,
  useHistoryStore,
} from "../stores/historyStore";
import DelayedTooltip from "./DelayedTooltip";

export default function ChatHistory() {
  const {
    selectConversation,
    deleteConversation,
    stopAnswering,
    clearHistory,
  } = useHistoryActions();
  const conversations = useHistoryStore((s) => s.conversations);
  const currentConversation = useHistoryStore((s) => s.currentConversation);

  const resetChat = () => {
    stopAnswering();
    clearHistory();
  };

  return (
    <div className="max-w-64 flex-grow space-y-2 overflow-auto rounded-bl-medium border-b-small border-l-small border-divider p-4">
      <div className="flex items-center justify-between gap-4">
        <p className="truncate text-small font-semibold leading-5 text-foreground">
          Conversations
        </p>
        <DelayedTooltip content="New chat" placement="right">
          <Button
            isIconOnly
            aria-label="New chat"
            variant="ghost"
            onPress={resetChat}
            data-testid="chat-history-clear-chat-button"
          >
            <Icon icon="heroicons:pencil-square" />
          </Button>
        </DelayedTooltip>
      </div>

      <div className="mt-2 flex flex-col gap-2">
        {Object.entries(conversations)
          .reverse()
          .map(([conversationKey, conversation]) => {
            if (!conversation.conversationId) {
              return null;
            }

            const isSelected =
              conversationKey === getConversationKey(currentConversation);
            return (
              <div className="flex gap-2" key={conversationKey}>
                <Button
                  variant={isSelected ? "solid" : "light"}
                  aria-label={`Select conversation ${conversationKey}`}
                  data-active={isSelected}
                  onPress={() => selectConversation(conversationKey)}
                  title={conversationKey}
                  data-testid={`select-conversation-${conversationKey}`}
                >
                  <div className="truncate text-small">
                    {/* TODO: Change to some summary later? */}
                    {conversationKey}
                  </div>
                </Button>
                <DelayedTooltip content="Delete conversation" placement="right">
                  <Button
                    isIconOnly
                    aria-label={`Delete conversation ${conversationKey}`}
                    onPress={() => deleteConversation(conversationKey)}
                    variant="ghost"
                    data-testid={`delete-conversation-${conversationKey}`}
                  >
                    <Icon icon="heroicons:trash" />
                  </Button>
                </DelayedTooltip>
              </div>
            );
          })}
      </div>
    </div>
  );
}
