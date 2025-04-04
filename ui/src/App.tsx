import { cn, ScrollShadow, useDisclosure } from "@heroui/react";
import Layout from "./core/components/Layout";
import ChatMessage from "./core/components/ChatMessage";
import { useState } from "react";
import { pluginManager } from "./core/utils/plugins/PluginManager";
import PromptInput from "./core/components/PromptInput/PromptInput";
import { createEventSource } from "./core/utils/eventSourceUtils";
import {
  FeedbackFormPlugin,
  FeedbackFormPluginName,
} from "./plugins/FeedbackFormPlugin";
import { mockSchema } from "./plugins/FeedbackFormPlugin/types.ts";
import PluginWrapper from "./core/utils/plugins/PluginWrapper.tsx";
import { ChatRequest, ChatResponseType, MessageRole } from "./types/api.ts";
import { useHistoryContext } from "./contexts/HistoryContext/useHistoryContext.ts";
import { useThemeContext } from "./contexts/ThemeContext/useThemeContext.ts";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function Component() {
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [message, setMessage] = useState<string>("");
  const { messages, createMessage, updateMessage } = useHistoryContext();
  const { theme } = useThemeContext();

  const { isOpen, onOpen, onOpenChange } = useDisclosure();

  const isFeedbackFormPluginActivated = pluginManager.isPluginActivated(
    FeedbackFormPluginName,
  );

  const onOpenFeedbackForm = () => {
    onOpen();
  };

  const handleSubmit = async () => {
    setIsLoading(true);

    createMessage({
      content: message,
      role: MessageRole.USER,
    });

    const assistantResponseId = createMessage({
      content: "",
      role: MessageRole.ASSISTANT,
    });

    const onError = () => {
      setIsLoading(false);
      // Add error message
      updateMessage(assistantResponseId, {
        type: ChatResponseType.TEXT,
        content: "An error occurred. Please try again.",
      });
    };

    createEventSource<ChatRequest>(
      `http://localhost:8000/api/chat`,
      (streamData) => {
        updateMessage(assistantResponseId, streamData);
      },
      onError,
      () => {
        setIsLoading(false);
      },
      {
        method: "POST",
        body: {
          message,
          history: messages.map((message) => ({
            role: message.role,
            content: message.content,
          })),
        },
      },
    );
  };

  // TODO: Fetch this from the server
  const heroMessage = `Hello! I'm your AI assistant. How can I help you today? You can ask me anything!
I also support markdown formatting. Which you can see **here**.`;

  const historyComponent = (
    <ScrollShadow className="flex h-full flex-col gap-6">
      {messages.map((message, idx) => (
        <ChatMessage
          key={idx}
          chatMessage={message}
          onOpenFeedbackForm={
            isFeedbackFormPluginActivated ? onOpenFeedbackForm : undefined
          }
        />
      ))}
    </ScrollShadow>
  );

  const heroComponent = (
    <div className="flex h-full w-full items-center justify-center">
      <div className="flex w-full max-w-[600px] flex-col gap-4">
        <Markdown
          className="text-large text-default-900"
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
  const content = messages.length > 0 ? historyComponent : heroComponent;

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
          schema: mockSchema,
          onClose: onOpenChange,
          isOpen,
          onSubmit: (data: Record<string, string>) => {
            console.log("Feedback form submitted:", data);
          },
        }}
      />
    </div>
  );
}
