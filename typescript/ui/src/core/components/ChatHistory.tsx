import { Button } from "@heroui/react";
import { Icon } from "@iconify/react";
import {
  getConversationKey,
  useHistoryActions,
  useHistoryStore,
} from "../stores/historyStore";

export default function ChatHistory() {
  const { selectConversation, deleteConversation } = useHistoryActions();
  const conversations = useHistoryStore((s) => s.conversations);
  const currentConversation = useHistoryStore((s) => s.currentConversation);

  return (
    <div className="max-w-64 flex-grow overflow-auto border-b-small border-l-small border-divider p-4">
      <p className="truncate text-small font-semibold leading-5 text-foreground">
        Previous conversations
      </p>
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
                <Button
                  isIconOnly
                  aria-label={`Delete conversation ${conversationKey}`}
                  onPress={() => deleteConversation(conversationKey)}
                  variant="ghost"
                  data-testid={`delete-conversation-${conversationKey}`}
                >
                  <Icon icon="heroicons:trash" />
                </Button>
              </div>
            );
          })}
      </div>
    </div>
  );
}
