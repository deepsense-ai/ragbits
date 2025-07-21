import { forwardRef, useState } from "react";
import { cn } from "@heroui/react";
import { MessageRole } from "@ragbits/api-client-react";

import { useHistoryStore, useMessage } from "../../stores/historyStore.ts";

import MarkdownContent from "./MarkdownContent.tsx";
import LiveUpdates from "./LiveUpdates.tsx";
import ImageGallery from "./ImageGallery.tsx";
import MessageReferences from "./MessageReferences.tsx";
import MessageActions from "./MessageActions.tsx";
import LoadingIndicator from "./LoadingIndicator.tsx";

type ChatMessageProps = {
  classNames?: {
    wrapper?: string;
    innerWrapper?: string;
    content?: string;
    liveUpdates?: string;
  };
  messageId: string;
};

const ChatMessage = forwardRef<HTMLDivElement, ChatMessageProps>(
  ({ messageId, classNames }, ref) => {
    const lastMessageId = useHistoryStore((s) => s.lastMessageId);
    const isHistoryLoading = useHistoryStore((s) => s.isLoading);
    const message = useMessage(messageId);

    if (!message) {
      throw new Error("Tried to render non-existent message");
    }

    const { serverId, content, role, references, liveUpdates, images } =
      message;
    const rightAlign = role === MessageRole.USER;
    const isLoading =
      isHistoryLoading &&
      role === MessageRole.ASSISTANT &&
      messageId === lastMessageId;

    const [didAnimate, setDidAnimate] = useState(false);

    return (
      <div
        ref={ref}
        data-testid="chat-message-wrapper"
        className={cn(
          "flex gap-3",
          { "flex-row-reverse": rightAlign },
          classNames?.wrapper,
        )}
      >
        <div
          className={cn(
            !didAnimate && "motion-safe:animate-pop-in",
            "flex flex-col gap-4",
            rightAlign && "max-w-[75%]",
            !rightAlign && "w-full",
          )}
          onAnimationEnd={() => setDidAnimate(true)}
        >
          <div
            className={cn(
              "relative rounded-medium px-4 py-3 text-default",
              rightAlign && "bg-default-100",
              classNames?.innerWrapper,
            )}
          >
            {rightAlign ? (
              <MarkdownContent
                content={content}
                classNames={classNames?.content}
              />
            ) : (
              <div className="flex flex-col gap-2">
                <LiveUpdates
                  isLoading={isLoading}
                  liveUpdates={liveUpdates}
                  classNames={{ liveUpdates: classNames?.liveUpdates }}
                />
                {isLoading && <LoadingIndicator content={content} />}
                <MarkdownContent
                  content={content}
                  classNames={classNames?.content}
                />
                {images && images.size > 0 && !isLoading && (
                  <ImageGallery images={images} />
                )}
                {references && references.length > 0 && !isLoading && (
                  <MessageReferences references={references} />
                )}
                <MessageActions
                  content={content}
                  serverId={serverId}
                  message={message}
                  isLoading={isLoading}
                />
              </div>
            )}
          </div>
        </div>
      </div>
    );
  },
);

export default ChatMessage;
