import React, { forwardRef, HTMLAttributes } from "react";
import { Button, cn } from "@heroui/react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

export type ChatMessageProps = HTMLAttributes<HTMLDivElement> & {
  name?: string;
  message: string;
  time?: string;
  isRTL?: boolean;
  classNames?: Record<"base", string>;
  onOpenFeedbackForm?: () => void;
};

const ChatMessage = forwardRef<HTMLDivElement, ChatMessageProps>(
  ({ name, time, message, isRTL, className, onOpenFeedbackForm }, ref) => {
    const messageRef = React.useRef<HTMLDivElement>(null);

    const Message = () => (
      <div className={cn("flex flex-col gap-4", isRTL && "max-w-[75%]")}>
        <div
          className={cn(
            "relative w-full rounded-medium px-4 py-3 text-default-600",
            isRTL && "bg-default-50",
          )}
        >
          {name && (
            <div className="flex">
              <div className="w-full text-small font-semibold text-default-foreground">
                {name}
              </div>
              <div className="flex-end text-small text-default-400">{time}</div>
            </div>
          )}
          <div
            ref={messageRef}
            className={cn("text-small text-default-900", name && "mt-2")}
          >
            {isRTL ? (
              <div className="whitespace-pre-line">{message}</div>
            ) : (
              <>
                <Markdown
                  className="prose max-w-full"
                  remarkPlugins={[remarkGfm]}
                >
                  {message}
                </Markdown>
                <div>
                  {!!onOpenFeedbackForm && (
                    <Button color="primary" onPress={onOpenFeedbackForm}>
                      Open Feedback Form
                    </Button>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    );

    return (
      <div
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
