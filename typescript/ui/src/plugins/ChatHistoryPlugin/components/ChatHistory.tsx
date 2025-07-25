import { Button } from "@heroui/react";
import { Icon } from "@iconify/react";
import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";
import DelayedTooltip from "../../../core/components/DelayedTooltip";
import { getConversationKey } from "../../../core/stores/HistoryStore/historyStore";
import { useHistoryActions } from "../../../core/stores/HistoryStore/selectors";
import { useHistoryStore } from "../../../core/stores/HistoryStore/useHistoryStore";

export default function ChatHistory() {
  const {
    selectConversation,
    deleteConversation,
    stopAnswering,
    clearHistory,
  } = useHistoryActions();
  const conversations = useHistoryStore((s) => s.conversations);
  const currentConversation = useHistoryStore((s) => s.currentConversation);
  const [isCollapsed, setCollapsed] = useState(false);
  const collapseButtonTitle = isCollapsed ? "Open sidebar" : "Close sidebar";
  const newChatIcon = <Icon icon="heroicons:pencil-square" />;

  const resetChat = () => {
    stopAnswering();
    clearHistory();
  };

  return (
    <motion.div
      initial={false}
      animate={{
        maxWidth: isCollapsed ? "4.5rem" : "16rem",
      }}
      className="rounded-l-medium border-small border-divider ml-4 flex h-full w-full min-w-[4.5rem] flex-grow flex-col space-y-2 overflow-hidden border-r-0 p-4 py-3"
    >
      <AnimatePresence>
        <DelayedTooltip
          content={collapseButtonTitle}
          placement="bottom"
          key="collapse-button"
        >
          <Button
            isIconOnly
            aria-label={collapseButtonTitle}
            variant="ghost"
            onPress={() => setCollapsed((c) => !c)}
            data-testid="chat-history-collapse-button"
            className="ml-auto"
          >
            <Icon
              icon={
                isCollapsed
                  ? "heroicons:chevron-double-right"
                  : "heroicons:chevron-double-left"
              }
            />
          </Button>
        </DelayedTooltip>
        {!isCollapsed && (
          <motion.p
            key="conversations"
            initial={false}
            animate={{
              opacity: 1,
              width: "100%",
              height: "auto",
            }}
            exit={{
              opacity: 0,
              width: 0,
              height: 0,
              marginBottom: 0,
            }}
            className="text-small text-foreground truncate leading-5 font-semibold"
          >
            Conversations
          </motion.p>
        )}

        <DelayedTooltip
          content="New conversation"
          placement="right"
          key="new-conversation-button"
        >
          <Button
            aria-label="New conversation"
            variant="ghost"
            onPress={resetChat}
            data-testid="chat-history-clear-chat-button"
            startContent={newChatIcon}
            isIconOnly={isCollapsed}
          >
            {!isCollapsed && "New conversation"}
          </Button>
        </DelayedTooltip>

        {!isCollapsed && (
          <motion.div
            className="mt-2 flex flex-1 flex-col gap-2 overflow-auto overflow-x-hidden"
            key="conversation-list"
            initial={false}
            animate={{
              opacity: 1,
              width: "100%",
            }}
            exit={{
              opacity: 0,
              width: 0,
            }}
          >
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
                      <div className="text-small truncate">
                        {/* TODO: Change to some summary later? */}
                        {conversationKey}
                      </div>
                    </Button>
                    <DelayedTooltip
                      content="Delete conversation"
                      placement="right"
                    >
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
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
