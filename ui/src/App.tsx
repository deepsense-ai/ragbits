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
import { ChatResponseType, MessageRole } from "./types/api.ts";
import { useHistoryContext } from "./contexts/HistoryContext/useHistoryContext.ts";
import { useThemeContext } from "./contexts/ThemeContext/useThemeContext.ts";

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

    createEventSource(
      `http://localhost:8000/api/chat`,
      (streamData) => {
        updateMessage(assistantResponseId, streamData);
      },
      onError,
      {
        method: "POST",
        body: {
          message,
        },
      },
    );
  };

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
            <ScrollShadow className="flex h-full flex-col gap-6">
              {messages.map((message, idx) => (
                <ChatMessage
                  key={idx}
                  chatMessage={message}
                  onOpenFeedbackForm={
                    isFeedbackFormPluginActivated
                      ? onOpenFeedbackForm
                      : undefined
                  }
                />
              ))}
            </ScrollShadow>
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
