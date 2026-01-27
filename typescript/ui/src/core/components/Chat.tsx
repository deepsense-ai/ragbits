import { Button, cn, ScrollShadow } from "@heroui/react";
import { useState, useRef, useEffect, useMemo, useCallback } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Icon } from "@iconify/react";
import {
  useMessageIds,
  useConversationProperty,
  useMessage,
  useHistoryActions,
  useHasPendingConfirmations,
} from "../stores/HistoryStore/selectors";
import { ChatMessage } from "./ChatMessage";
import QuickMessageInput from "./inputs/QuickMessageInput";
import { useConfigContext } from "../contexts/ConfigContext/useConfigContext";
import { useRagbitsContext } from "@ragbits/api-client-react";
import { PromptInputProps } from "./inputs/PromptInput/PromptInput";

interface ChatProps {
  pluginSlots?: PromptInputProps["pluginSlots"] & {};
}

export default function Chat({ pluginSlots }: ChatProps) {
  const {
    config: { customization },
  } = useConfigContext();
  const messageIds = useMessageIds();
  const lastMessageId = useConversationProperty((s) => s.lastMessageId);
  const lastMessage = useMessage(lastMessageId);
  const historyIsLoading = useConversationProperty((s) => s.isLoading);
  const followupMessages = useConversationProperty((s) => s.followupMessages);
  const hasPendingConfirmations = useHasPendingConfirmations();
  const { sendMessage, stopAnswering } = useHistoryActions();
  const [showScrollDownButton, setShowScrollDownButton] = useState(false);
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);

  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const showHistory = useMemo(() => messageIds.length > 0, [messageIds.length]);
  const { client: ragbitsClient } = useRagbitsContext();

  const authorizedSendMessage = (text: string) => {
    sendMessage(text, ragbitsClient);
  };

  const handleScroll = useCallback(() => {
    const AUTO_SCROLL_THRESHOLD = 25;
    const SCROLL_DOWN_THRESHOLD = 100;

    if (!scrollContainerRef.current) return;

    const container = scrollContainerRef.current;
    const offsetFromBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight;

    setShowScrollDownButton(offsetFromBottom > SCROLL_DOWN_THRESHOLD);
    setShouldAutoScroll(false);

    if (offsetFromBottom > AUTO_SCROLL_THRESHOLD) {
      setShouldAutoScroll(false);
    } else {
      setShouldAutoScroll(true);
    }
  }, []);

  useEffect(() => {
    setShouldAutoScroll(true);

    if (messageIds.length === 0) {
      setShowScrollDownButton(false);
    }
  }, [messageIds.length]);

  useEffect(() => {
    if (!scrollContainerRef.current) return;

    if (shouldAutoScroll) {
      const container = scrollContainerRef.current;
      container.scrollTop = container.scrollHeight;
    }
  }, [handleScroll, lastMessage, shouldAutoScroll]);

  useEffect(() => {
    const container = scrollContainerRef.current;
    container?.addEventListener("scroll", handleScroll);

    return () => {
      container?.removeEventListener("scroll", handleScroll);
    };
  }, [handleScroll, showHistory]);

  const scrollToBottom = useCallback(() => {
    if (!scrollContainerRef.current) return;

    scrollContainerRef.current.scrollTo({
      top: scrollContainerRef.current.scrollHeight,
      behavior: "smooth",
    });

    setShouldAutoScroll(true);
  }, []);
  const historyComponent = useMemo(
    () => (
      <ScrollShadow
        className="relative flex h-full flex-col gap-6 pb-8"
        ref={scrollContainerRef}
      >
        {messageIds.map((m) => (
          <ChatMessage key={m} messageId={m} />
        ))}
      </ScrollShadow>
    ),
    [messageIds],
  );

  const heroComponent = (
    <div className="flex h-full w-full items-center justify-center">
      <div className="flex w-full max-w-[600px] flex-col gap-4">
        {customization?.welcome_message && (
          <Markdown
            className="text-large text-default-900 text-center"
            remarkPlugins={[remarkGfm]}
          >
            {customization?.welcome_message}
          </Markdown>
        )}
        <div className="text-small text-default-500 text-center">
          You can start a conversation by typing in the input box below.
        </div>
      </div>
    </div>
  );

  const content = showHistory ? historyComponent : heroComponent;
  return (
    <div className="relative flex h-full flex-col overflow-y-auto p-6 pb-8">
      {content}
      <div className="relative mt-auto flex max-w-full flex-col gap-2 px-6">
        {/* Floating Scroll-to-bottom button */}
        <Button
          variant="solid"
          onPress={scrollToBottom}
          className={cn(
            "absolute -top-16 left-1/2 z-10 -translate-x-1/2 transition-all duration-200 ease-out",
            showScrollDownButton && showHistory
              ? "opacity-100"
              : "pointer-events-none opacity-0",
          )}
          tabIndex={-1}
          startContent={<Icon icon="heroicons:arrow-down" />}
        >
          Scroll to bottom
        </Button>
        <QuickMessageInput
          isLoading={historyIsLoading}
          submit={authorizedSendMessage}
          stopAnswering={stopAnswering}
          followupMessages={followupMessages}
          isDisabled={hasPendingConfirmations}
          pluginSlots={{ "chat-options": pluginSlots?.["chat-options"] }}
        />
      </div>
    </div>
  );
}
