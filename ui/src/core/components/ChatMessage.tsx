import { forwardRef } from "react";
import { Button, cn } from "@heroui/react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage } from "../../types/chat";
import { MessageRole } from "../../types/api";

export type ChatMessageProps = {
  classNames?: string[];
  chatMessage: ChatMessage;
  onOpenFeedbackForm?: () => void;
};

const ChatMessage = forwardRef<HTMLDivElement, ChatMessageProps>(
  ({ chatMessage: { content, role }, onOpenFeedbackForm, classNames }, ref) => {
    const rightAlign = role === MessageRole.USER;

    const Message = () => (
      <div className={cn("flex flex-col gap-4", rightAlign && "max-w-[75%]")}>
        <div
          className={cn(
            "relative w-full rounded-medium px-4 py-3 text-default",
            rightAlign && "bg-default-100",
          )}
        >
          <div className={cn("text-small text-default-900")}>
            {rightAlign ? (
              <div className="whitespace-pre-line">{content}</div>
            ) : (
              <>
                <Markdown
                  className="max-w-full text-default-900"
                  remarkPlugins={[remarkGfm]}
                >
                  {content}
                </Markdown>
                <div className="mt-2">
                  {!!onOpenFeedbackForm && (
                    <Button variant="ghost" onPress={onOpenFeedbackForm}>
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
        className={cn(
          "flex gap-3",
          { "flex-row-reverse": rightAlign },
          ...(classNames ? classNames : []),
        )}
      >
        <Message />
      </div>
    );
  },
);

ChatMessage.displayName = "ChatMessage";

export default ChatMessage;
