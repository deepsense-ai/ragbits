import { ScrollShadow } from "@heroui/react";
import Layout from "./core/components/Layout";
import ChatMessage, { ChatMessageProps } from "./core/components/ChatMessage";
import { useEffect, useState } from "react";
import PluginWrapper from "./core/utils/plugins/PluginWrapper";
import { ExamplePlugin, ExamplePluginName } from "./plugins/ExamplePlugin";
import { pluginManager } from "./core/utils/plugins/PluginManager";
import PromptInput from "./core/components/PromptInput/PromptInput";
import { createEventSource } from "./core/utils/eventSourceUtils";
import axiosWrapper from "./core/utils/axiosWrapper";

export default function Component() {
  const [messages, setMessages] = useState<Array<ChatMessageProps>>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [message, setMessage] = useState<string>("");

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

    setMessages((state) => [
      ...state,
      {
        name: "You",
        message,
        isRTL: true,
      },
    ]);

    const onError = () => {
      setIsLoading(false);
      // Add error message
      setMessages((state) => [
        ...state,
        {
          name: "Ragbits",
          message: "An error occurred. Please try again.",
        },
      ]);
    };

    const [data, error] = await axiosWrapper<{ id: string }>({
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

    const cleanUp = createEventSource<string>(
      `http://localhost:8000/api/chat/${data.id}`,
      (data) => {
        setMessages((state) => {
          if (state[state.length - 1].name === "You") {
            return [
              ...state,
              {
                name: "Ragbits",
                message: data,
              },
            ];
          } else {
            return state.map((item, index) =>
              index === state.length - 1
                ? { ...item, message: item.message + data }
                : item,
            );
          }
        });
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
        <div className="relative flex h-full flex-col overflow-y-auto p-6 pb-8">
          <ScrollShadow className="flex h-full flex-col gap-6">
            {messages.map((message, idx) => (
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
        <PluginWrapper plugin={ExamplePlugin} component="ExampleComponent" />
      </Layout>
    </div>
  );
}
