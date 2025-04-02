import { Button, ScrollShadow, useDisclosure } from "@heroui/react";
import Layout from "./core/components/Layout";
import ChatMessage from "./core/components/ChatMessage";
import { useState } from "react";
import { pluginManager } from "./core/utils/plugins/PluginManager";
import PromptInput from "./core/components/PromptInput/PromptInput";
import { createEventSource } from "./core/utils/eventSourceUtils";
import axiosWrapper from "./core/utils/axiosWrapper";
import { useChatHistory } from "./contexts/HistoryContext/HistoryContext.tsx";
import {
  FeedbackFormPlugin,
  FeedbackFormPluginName,
} from "./plugins/FeedbackFormPlugin";
import { mockSchema } from "./plugins/FeedbackFormPlugin/types.ts";
import PluginWrapper from "./core/utils/plugins/PluginWrapper.tsx";
import { SubmitHandler } from "react-hook-form";

export default function Component() {
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [message, setMessage] = useState<string>("");
  const { messages, createMessage, updateMessage, clearMessages } =
    useChatHistory();

  const { isOpen, onOpen, onOpenChange } = useDisclosure();

  const isFeedbackFormPluginActivated = pluginManager.isPluginActivated(
    FeedbackFormPluginName,
  );

  const onOpenFeedbackForm = () => {
    onOpen();
  };

  const handleSubmit = async () => {
    setIsLoading(true);

    const id = createMessage({
      name: "You",
      message,
      isRTL: true,
    });

    const onError = () => {
      setIsLoading(false);
      // Add error message
      createMessage({
        name: "Ragbits",
        message: "An error occurred. Please try again.",
      });
    };

    const [, error] = await axiosWrapper({
      url: "http://localhost:8000/api/chat",
      method: "POST",
      body: { message },
    });

    if (error) {
      console.error("Failed to send message:", error);
      onError();
      return () => {
        setIsLoading(false);
      };
    }

    createMessage({
      id: id,
      name: "Ragbits",
      message: "",
    });

    const cleanUp = createEventSource<string>(
      `http://localhost:8000/api/chat`,
      (streamData) => {
        updateMessage(id, streamData);
      },
      onError,
    );

    return () => {
      cleanUp();
      setIsLoading(false);
    };
  };

  return (
    <>
      <div className="h-full w-full max-w-full">
        <Layout subTitle="by deepsense.ai" title="Ragbits Chat">
          <Button color="primary" onPress={clearMessages}>
          Clear chat
        </Button>
        <div className="relative flex h-full flex-col overflow-y-auto p-6 pb-8">
            <ScrollShadow className="flex h-full flex-col gap-6">
              {messages.map((message, idx) => (
                <ChatMessage
                  key={idx}
                  classNames={{
                    base: "bg-default-50",
                  }}
                  {...message}
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
        pluginProps={{
          title: "Feedback Form",
          schema: mockSchema,
          isOpen,
          onClose: onOpenChange,
          onSubmit: (data: SubmitHandler<Record<string, string>>) => {
            console.log("Feedback form submitted:", data);
          },
        }}
      />
    </>
  );
}
