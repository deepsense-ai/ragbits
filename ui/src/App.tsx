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
import { ConfigResponse, FormType } from "./types/api.ts";
import { useHistoryContext } from "./contexts/HistoryContext/useHistoryContext.ts";
import { useThemeContext } from "./contexts/ThemeContext/useThemeContext.ts";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Icon } from "@iconify/react/dist/iconify.js";
import { buildApiUrl } from "./core/utils/api.ts";
import { useRequest } from "./core/utils/request.ts";

export default function Component() {
  const [config, setConfig] = useState<ConfigResponse | null>(null);
  const [message, setMessage] = useState<string>("");
  const [showScrollDownButton, setShowScrollDownButton] = useState(false);
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);
  const [feedbackName, setFeedbackName] = useState<FormType>();
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
  const configRequest = useRequest<ConfigResponse>(buildApiUrl("/api/config"));

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
    if (configRequest.data) {
      const config = configRequest.data.data;
      setConfig(config);
    }
  }, [configRequest.data]);

  useEffect(() => {
    if (!config) {
      return;
    }

    if (
      Object.prototype.hasOwnProperty.call(config, FormType.LIKE) ||
      Object.prototype.hasOwnProperty.call(config, FormType.DISLIKE)
    ) {
      pluginManager.activate(FeedbackFormPluginName);
    }
  }, [config]);

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
    console.log("Feedback form submitted:", data);
  };

  const onOpenFeedbackForm = async (name: typeof feedbackName) => {
    setFeedbackName(name);

    if (config![name as keyof typeof config] === null) {
      await onFeedbackFormSubmit(null);
      return;
    }

    onOpen();
  };

  const handleSubmit = () => {
    sendMessage(message);
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
          likeForm={config?.["like_form"]}
          dislikeForm={config?.["dislike_form"]}
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
  const isLoading = configRequest.isLoading || historyIsLoading;

  return (
    <div
      className={cn(
        "flex h-screen w-screen items-start justify-center bg-background",
        theme,
      )}
    >
      <div className="h-full w-full max-w-full">
        <Layout subTitle="by deepsense.ai" title="Ragbits Chat">
          <div className="relative flex h-full flex-col overflow-y-auto p-6 pb-8">
            {content}

            {/* Floating Scroll-to-bottom button */}
            <Button
              variant="solid"
              onPress={scrollToBottom}
              className={cn(
                "absolute bottom-32 left-1/2 z-10 -translate-x-1/2 transition-all duration-200 ease-out",
                showScrollDownButton && showHistory
                  ? "opacity-100"
                  : "pointer-events-none opacity-0",
              )}
              tabIndex={-1}
              startContent={<Icon icon="heroicons:arrow-down" />}
            >
              Scroll to bottom
            </Button>

            <div className="mt-auto flex max-w-full flex-col gap-2 px-6">
              <PromptInput
                isLoading={isLoading}
                submit={handleSubmit}
                message={message}
                setMessage={setMessage}
              />
            </div>
          </div>
        </Layout>
      </div>
      <PluginWrapper
        plugin={FeedbackFormPlugin}
        component="FeedbackFormComponent"
        componentProps={{
          title: "Feedback Form",
          schema:
            config && feedbackName
              ? !config[feedbackName]
                ? { title: "", fields: [] }
                : config[feedbackName]
              : { title: "", fields: [] },
          onClose: onOpenChange,
          onSubmit: onFeedbackFormSubmit,
          isOpen,
        }}
      />
    </div>
  );
}
