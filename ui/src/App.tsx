import { Button, ScrollShadow } from "@heroui/react";
import Layout from "./core/components/Layout";
import ChatMessage from "./core/components/ChatMessage";
import { useEffect, useState } from "react";
import { ExamplePluginName } from "./plugins/ExamplePlugin";
import { pluginManager } from "./core/utils/plugins/PluginManager";
import PromptInput from "./core/components/PromptInput/PromptInput";
import { createEventSource } from "./core/utils/eventSourceUtils";
import axiosWrapper from "./core/utils/axiosWrapper";
import { useChatHistory } from "./contexts/HistoryContext/HistoryContext.tsx";

export default function Component() {
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [message, setMessage] = useState<string>("");
  const { messages, createMessage, updateMessage, clearMessages } =
    useChatHistory();

  useEffect(() => {
    // Delay loading of plugin to demonstrate lazy loading
    const timeout = setTimeout(() => {
      pluginManager.activate(ExamplePluginName);
    }, 5000);

    return () => {
      clearTimeout(timeout);
    };
  }, []);

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
    <div className="h-full w-full max-w-full">
      <Layout subTitle="by deepsense.ai" title="Ragbits Chat">
        <Button color="primary" onPress={clearMessages}>
          Clear chat
        </Button>
        <div className="relative flex h-full flex-col overflow-y-auto p-6 pb-8">
          <ScrollShadow className="flex h-full flex-col gap-6">
            {Array.from(messages.values()).map((message, idx) => (
              <ChatMessage
                key={idx}
                classNames={{
                  base: "bg-default-50",
                }}
                {...message}
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
  );
}
