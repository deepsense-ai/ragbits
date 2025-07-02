import { Button, cn, ScrollShadow } from "@heroui/react";
import Layout from "./core/components/Layout";
import ChatMessage from "./core/components/ChatMessage";
import { useState, useRef, useEffect, useMemo, useCallback } from "react";
import PromptInput from "./core/components/PromptInput/PromptInput";
import { useHistoryContext } from "./core/contexts/HistoryContext/useHistoryContext";
import { useThemeContext } from "./core/contexts/ThemeContext/useThemeContext";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Icon } from "@iconify/react";
import { useConfigContext } from "./core/contexts/ConfigContext/useConfigContext";
import { DEFAULT_LOGO, DEFAULT_SUBTITLE, DEFAULT_TITLE } from "./config";

export default function App() {
  const {
    config: { customization },
  } = useConfigContext();
  const {
    history,
    isLoading: historyIsLoading,
    followupMessages,
    sendMessage,
    stopAnswering,
  } = useHistoryContext();
  const { theme } = useThemeContext();
  const [showScrollDownButton, setShowScrollDownButton] = useState(false);
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);

  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const showHistory = useMemo(() => history.length > 0, [history.length]);

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

  const handleSubmit = (text: string) => {
    sendMessage(text);
  };

  const historyComponent = (
    <ScrollShadow
      className="relative flex h-full flex-col gap-6 pb-8"
      ref={scrollContainerRef}
    >
      {history.map((m) => (
        <ChatMessage
          key={m.id}
          chatMessage={m}
          isLoading={
            historyIsLoading &&
            m.role === "assistant" &&
            m.id === history[history.length - 1].id
          }
        />
      ))}
    </ScrollShadow>
  );

  const heroComponent = (
    <div className="flex h-full w-full items-center justify-center">
      <div className="flex w-full max-w-[600px] flex-col gap-4">
        {customization?.welcome_message && (
          <Markdown
            className="text-center text-large text-default-900"
            remarkPlugins={[remarkGfm]}
          >
            {customization?.welcome_message}
          </Markdown>
        )}
        <div className="text-center text-small text-default-500">
          You can start a conversation by typing in the input box below.
        </div>
      </div>
    </div>
  );

  const content = showHistory ? historyComponent : heroComponent;
  const logo = customization?.header?.logo ?? DEFAULT_LOGO;
  const title = customization?.header?.title ?? DEFAULT_TITLE;
  const subTitle = customization?.header?.subtitle ?? DEFAULT_SUBTITLE;

  return (
    <div
      className={cn(
        "flex h-screen w-screen items-start justify-center bg-background",
        theme,
      )}
    >
      <div className="h-full w-full max-w-full">
        <Layout subTitle={subTitle} title={title} logo={logo}>
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
              <PromptInput
                isLoading={historyIsLoading}
                submit={handleSubmit}
                stopAnswering={stopAnswering}
                followupMessages={followupMessages}
                history={history}
              />
            </div>
          </div>
        </Layout>
      </div>
    </div>
  );
}
