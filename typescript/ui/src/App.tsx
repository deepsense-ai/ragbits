import { Button, cn, ScrollShadow, useDisclosure } from "@heroui/react";
import Layout from "./core/components/Layout";
import ChatMessage from "./core/components/ChatMessage";
import { useState, useRef, useEffect, useMemo, useCallback } from "react";
import { pluginManager } from "./core/utils/plugins/PluginManager";
import PromptInput from "./core/components/PromptInput/PromptInput";
import {
  FeedbackFormPlugin,
  FeedbackFormPluginName,
} from "./plugins/FeedbackFormPlugin";
import PluginWrapper from "./core/utils/plugins/PluginWrapper.tsx";
import { FormEnabler, FormType, FormSchemaResponse } from "./types/api.ts";
import { useHistoryContext } from "./contexts/HistoryContext/useHistoryContext.ts";
import { useThemeContext } from "./contexts/ThemeContext/useThemeContext.ts";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Icon } from "@iconify/react/dist/iconify.js";
import { useRagbitsCall, type FeedbackRequest } from "ragbits-api-client-react";

export default function App() {
  const [message, setMessage] = useState<string>("");
  const [showScrollDownButton, setShowScrollDownButton] = useState(false);
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);
  const [feedbackName, setFeedbackName] = useState<FormType>();
  const [feedbackMessageId, setFeedbackMessageId] = useState<string | null>(
    null,
  );

  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const {
    history,
    sendMessage,
    isLoading: historyIsLoading,
  } = useHistoryContext();
  const { theme } = useThemeContext();
  const { isOpen, onOpen, onOpenChange } = useDisclosure();
  const isFeedbackFormPluginActivated = pluginManager.isPluginActivated(
    FeedbackFormPluginName,
  );
  const showHistory = useMemo(() => history.length > 0, [history.length]);

  // Use the new generic hooks
  const config = useRagbitsCall<Record<string, unknown>>("/api/config");
  const feedback = useRagbitsCall<{ success: boolean }>("/api/feedback", {
    method: "POST",
  });

  // Load config on mount
  useEffect(() => {
    config.call().catch(console.error);
  }, []);

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
    if (!config.data) {
      return;
    }

    if (config.data[FormEnabler.LIKE] || config.data[FormEnabler.DISLIKE]) {
      pluginManager.activate(FeedbackFormPluginName);
    }
  }, [config.data]);

  useEffect(() => {
    setShouldAutoScroll(true);

    if (history.length === 0) {
      setShowScrollDownButton(false);
    }
  }, [history.length]);

  useEffect(() => {
    if (!scrollContainerRef.current) return;

    if (shouldAutoScroll) {
      const container = scrollContainerRef.current;
      container.scrollTop = container.scrollHeight;
    }
  }, [handleScroll, history, shouldAutoScroll]);

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

  const onFeedbackFormSubmit = async (data: Record<string, string> | null) => {
    try {
      await feedback.call({
        body: {
          message_id: feedbackMessageId!,
          feedback: feedbackName!,
          payload: data,
        } as FeedbackRequest,
      });
    } catch (e) {
      console.error(e);
      // TODO: Add some information to the UI about error
    }
  };

  const onOpenFeedbackForm = async (id: string, name: typeof feedbackName) => {
    setFeedbackName(name);
    setFeedbackMessageId(id);

    if (config.data![name as keyof typeof config.data] === null) {
      await onFeedbackFormSubmit(null);
      return;
    }

    onOpen();
  };

  const handleSubmit = () => {
    sendMessage(message);
    setMessage("");
  };

  const heroMessage = `Hello! I'm your AI assistant.\n\n How can I help you today?
You can ask me anything! I can provide information, answer questions, and assist you with various tasks.`;

  const historyComponent = (
    <ScrollShadow
      className="relative flex h-full flex-col gap-6 pb-8"
      ref={scrollContainerRef}
    >
      {history.map((m) => (
        <ChatMessage
          key={m.id}
          chatMessage={m}
          onOpenFeedbackForm={
            isFeedbackFormPluginActivated ? onOpenFeedbackForm : undefined
          }
          likeForm={
            (config.data?.[FormType.LIKE] as FormSchemaResponse) || null
          }
          dislikeForm={
            (config.data?.[FormType.DISLIKE] as FormSchemaResponse) || null
          }
        />
      ))}
    </ScrollShadow>
  );

  const heroComponent = (
    <div className="flex h-full w-full items-center justify-center">
      <div className="flex w-full max-w-[600px] flex-col gap-4">
        <Markdown
          className="text-center text-large text-default-900"
          remarkPlugins={[remarkGfm]}
        >
          {heroMessage}
        </Markdown>
        <div className="text-center text-small text-default-500">
          You can start a conversation by typing in the input box below.
        </div>
      </div>
    </div>
  );

  const content = showHistory ? historyComponent : heroComponent;
  const isLoading = config.isLoading || historyIsLoading;

  return (
    <div
      className={cn(
        "flex h-screen w-screen items-start justify-center bg-background",
        theme,
      )}
    >
      <Layout>
        <div className="relative flex h-full flex-col">
          <div className="flex-1 overflow-hidden">{content}</div>
          {showScrollDownButton && (
            <Button
              isIconOnly
              variant="flat"
              aria-label="Scroll to bottom"
              className="absolute bottom-24 right-6 z-20"
              onClick={scrollToBottom}
            >
              <Icon icon="heroicons:arrow-down-20-solid" />
            </Button>
          )}
          <div className="mt-auto">
            <PromptInput
              message={message}
              setMessage={setMessage}
              submit={handleSubmit}
              isLoading={isLoading}
            />
          </div>
        </div>
      </Layout>
      {isFeedbackFormPluginActivated && (
        <PluginWrapper
          plugin={FeedbackFormPlugin}
          component="FeedbackFormComponent"
          componentProps={{
            title: feedbackName || "Feedback",
            isOpen,
            onClose: () => onOpenChange(),
            onSubmit: onFeedbackFormSubmit,
            schema: feedbackName
              ? (config.data?.[
                  feedbackName as keyof typeof config.data
                ] as FormSchemaResponse)
              : null,
          }}
        />
      )}
    </div>
  );
}
