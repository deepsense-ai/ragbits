import { ScrollShadow } from "@heroui/react";

import SidebarContainer from "./sidebar-with-chat-history";
import MessagingChatMessage from "./messaging-chat-message";

import PromptInputWithEnclosedActions from "./prompt-input-with-enclosed-actions";
import { useState } from "react";
import { MessagingChatMessageProps } from "./data";

export default function Component() {
  const [messages, setMessages] = useState<Array<MessagingChatMessageProps>>(
    [],
  );
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [message, setMessage] = useState<string>("");

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

    const res = await fetch("http://localhost:8000/api/chat", {
      method: "POST",
      body: JSON.stringify({
        message,
      }),
    });

    const data = await res.json();

    const eventSource = new EventSource(
      `http://localhost:8000/api/chat/${data.id}`,
    );

    eventSource.onmessage = (event) => {
      const { data } = event;

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
    };

    eventSource.onerror = (error) => {
      console.error("EventSource failed:", error);
      eventSource.close();
      setIsLoading(false);
    };

    return () => {
      eventSource.close();
      setIsLoading(false);
    };
  };

  return (
    <div className="h-full w-full max-w-full">
      <SidebarContainer subTitle="by deepsense.ai" title="Ragbits Chat">
        <div className="relative flex h-full flex-col overflow-y-auto p-6 pb-8">
          <ScrollShadow className="flex h-full flex-col gap-6">
            {messages.map((message, idx) => (
              <MessagingChatMessage
                key={idx}
                classNames={{
                  base: "bg-default-50",
                }}
                {...message}
              />
            ))}
          </ScrollShadow>
          <div className="mt-auto flex max-w-full flex-col gap-2 px-6">
            <PromptInputWithEnclosedActions
              isLoading={isLoading}
              submit={handleSubmit}
              message={message}
              setMessage={setMessage}
            />
          </div>
        </div>
      </SidebarContainer>
    </div>
  );
}
