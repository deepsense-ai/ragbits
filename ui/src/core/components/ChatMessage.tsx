import React, { forwardRef, HTMLAttributes } from "react";
import { cn } from "@heroui/react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

export type ChatMessageProps = HTMLAttributes<HTMLDivElement> & {
  name: string;
  message: string;
  time?: string;
  isRTL?: boolean;
  classNames?: Record<"base", string>;
};

const ChatMessage = forwardRef<HTMLDivElement, ChatMessageProps>(
  ({ name, time, message, isRTL, className, classNames, ...props }, ref) => {
    const messageRef = React.useRef<HTMLDivElement>(null);

    const Message = () => (
      <div className="flex max-w-[70%] flex-col gap-4">
        <div
          className={cn(
            "relative w-full rounded-medium bg-content2 px-4 py-3 text-default-600",
            classNames?.base,
          )}
        >
          <div className="flex">
            <div className="w-full text-small font-semibold text-default-foreground">
              {name}
            </div>
            <div className="flex-end text-small text-default-400">{time}</div>
          </div>
          <div ref={messageRef} className="mt-2 text-small text-default-900">
            {isRTL ? (
              <div className="whitespace-pre-line">{message}</div>
            ) : (
              <Markdown
                className="prose max-w-full"
                remarkPlugins={[remarkGfm]}
              >
                {message}
              </Markdown>
            )}
          </div>
        </div>
      </div>
    );

    return (
      <div
        {...props}
        ref={ref}
        className={cn("flex gap-3", { "flex-row-reverse": isRTL }, className)}
      >
        <Message />
      </div>
    );
  },
);

ChatMessage.displayName = "MessagingChatMessage";

export default ChatMessage;
