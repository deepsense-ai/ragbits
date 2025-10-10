import {
  Button,
  Dropdown,
  DropdownItem,
  DropdownMenu,
  DropdownTrigger,
  Input,
} from "@heroui/react";
import { Icon } from "@iconify/react";
import { motion, AnimatePresence } from "framer-motion";
import { useRef, useState } from "react";
import DelayedTooltip from "../../../core/components/DelayedTooltip";
import { useHistoryActions } from "../../../core/stores/HistoryStore/selectors";
import { useHistoryStore } from "../../../core/stores/HistoryStore/useHistoryStore";
import { isTemporaryConversation } from "../../../core/stores/HistoryStore/historyStore";
import { useNavigate } from "react-router";
import { getConversationRoute } from "../utils";
import { useShallow } from "zustand/shallow";
import { zip } from "lodash";

export default function ChatHistory() {
  const {
    selectConversation,
    deleteConversation,
    newConversation,
    setConversationProperties,
  } = useHistoryActions();
  const navigate = useNavigate();
  const conversations = useHistoryStore(
    useShallow((s) => Object.keys(s.conversations).reverse()),
  );
  const summaries = useHistoryStore(
    useShallow((s) =>
      Object.values(s.conversations)
        .reverse()
        .map((entry) => entry.summary),
    ),
  );
  const currentConversation = useHistoryStore((s) => s.currentConversation);
  const [isCollapsed, setCollapsed] = useState(false);
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const [ignoreBlur, setIgnoreBlur] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const collapseButtonTitle = isCollapsed ? "Open sidebar" : "Close sidebar";
  const newChatIcon = <Icon icon="heroicons:pencil-square" />;

  const handleStartEdit = (conversationKey: string, currentSummary: string) => {
    setEditingKey(conversationKey);
    setEditValue(currentSummary ?? "");
    setIgnoreBlur(true);
    setTimeout(() => {
      inputRef.current?.focus?.();
      setTimeout(() => setIgnoreBlur(false), 120);
    }, 0);
  };

  const handleSaveEdit = (conversationKey: string) => {
    if (editingKey !== conversationKey) return;
    const trimmed = (editValue || "").trim();
    if (trimmed) {
      setConversationProperties(conversationKey, { summary: trimmed });
    }
    setEditingKey(null);
    setEditValue("");
    setIgnoreBlur(false);
  };

  const handleCancelEdit = () => {
    setEditingKey(null);
    setEditValue("");
    setIgnoreBlur(false);
  };

  const handleNewConversation = () => {
    const conversationId = newConversation();
    navigate(getConversationRoute(conversationId));
  };

  const handleNavigate = (conversationId: string) => {
    selectConversation(conversationId);
    navigate(getConversationRoute(conversationId));
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
            onPress={handleNewConversation}
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
            {zip(conversations, summaries).map(([conversation, summary]) => {
              if (!conversation || isTemporaryConversation(conversation)) {
                return null;
              }

              const isSelected = conversation === currentConversation;
              const isEdited = conversation === editingKey;
              const variant = isSelected ? "solid" : "light";
              return (
                <div
                  className="flex w-full justify-between gap-2"
                  key={`${conversation}-${variant}`}
                >
                  {isEdited ? (
                    <Input
                      ref={inputRef}
                      size="sm"
                      variant="bordered"
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      onBlur={() => {
                        if (ignoreBlur) return;
                        handleSaveEdit(conversation);
                      }}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") handleSaveEdit(conversation);
                        if (e.key === "Escape") handleCancelEdit();
                      }}
                      className="flex-1"
                      data-testid={`input-conversation-${conversation}`}
                    />
                  ) : (
                    <Button
                      variant={variant}
                      aria-label={`Select conversation ${conversation}`}
                      data-active={isSelected}
                      onPress={() => handleNavigate(conversation)}
                      title={summary ?? conversation}
                      data-testid={`select-conversation-${conversation}`}
                      className="flex-1 justify-start"
                    >
                      <div className="text-small truncate">
                        {summary ?? conversation}
                      </div>
                    </Button>
                  )}
                  <Dropdown>
                    <DropdownTrigger>
                      <Button
                        isIconOnly
                        variant="light"
                        aria-label={`Conversation actions for ${conversation}`}
                        data-testid={`dropdown-conversation-${conversation}`}
                      >
                        <Icon
                          icon="heroicons:ellipsis-vertical"
                          className="rotate-90"
                        />
                      </Button>
                    </DropdownTrigger>
                    <DropdownMenu aria-label="Conversation actions">
                      <DropdownItem
                        key="edit"
                        startContent={
                          <Icon
                            icon="heroicons:pencil-square"
                            className="mb-0.5"
                          />
                        }
                        onPress={() =>
                          handleStartEdit(conversation, summary ?? conversation)
                        }
                        data-testid={`edit-conversation-${conversation}`}
                      >
                        Edit
                      </DropdownItem>
                      <DropdownItem
                        key="delete"
                        className="text-danger mb-0.5"
                        color="danger"
                        startContent={<Icon icon="heroicons:trash" />}
                        onPress={() => deleteConversation(conversation)}
                        data-testid={`delete-conversation-${conversation}`}
                      >
                        Delete conversation
                      </DropdownItem>
                    </DropdownMenu>
                  </Dropdown>
                </div>
              );
            })}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
