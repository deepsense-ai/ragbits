import { forwardRef, useState } from "react";
import { cn } from "@heroui/react";
import { Icon } from "@iconify/react";

import MarkdownContent from "./MarkdownContent.tsx";
import LiveUpdates from "./LiveUpdates.tsx";
import ImageGallery from "./ImageGallery.tsx";
import MessageReferences from "./MessageReferences.tsx";
import MessageActions from "./MessageActions.tsx";
import LoadingIndicator from "./LoadingIndicator.tsx";
import {
  useConversationProperty,
  useMessage,
} from "../../stores/HistoryStore/selectors.ts";
import { MessageRole } from "@ragbits/api-client";

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
    const lastMessageId = useConversationProperty((s) => s.lastMessageId);
    const isHistoryLoading = useConversationProperty((s) => s.isLoading);
    const message = useMessage(messageId);

    if (!message) {
      throw new Error("Tried to render non-existent message");
    }

    const {
      serverId,
      content,
      role,
      references,
      liveUpdates,
      images,
      confirmationRequests,
      confirmationStates,
      error,
    } = message;
    const rightAlign = role === MessageRole.User;
    const isLoading =
      isHistoryLoading &&
      role === MessageRole.Assistant &&
      messageId === lastMessageId;

    const [didAnimate, setDidAnimate] = useState(false);

    const showLoadingIndicator = isLoading && !liveUpdates && !content.length;
    const showMessageActions = !isLoading;
    const showImageGallery =
      !isLoading && images && Object.keys(images).length > 0;
    const showMessageReferences =
      !isLoading && references && references.length > 0;
    const showLiveUpdates = liveUpdates;

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
              "rounded-medium text-default relative px-4 py-3",
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
                {showLoadingIndicator && <LoadingIndicator />}
                {showLiveUpdates && (
                  <LiveUpdates
                    shouldShimmer={isLoading}
                    liveUpdates={liveUpdates}
                    classNames={{ liveUpdates: classNames?.liveUpdates }}
                  />
                )}
                <MarkdownContent
                  content={content}
                  classNames={classNames?.content}
                />
                {error && (
                  <div
                    data-testid="message-error"
                    className="bg-danger-50 border-danger-200 text-danger-700 rounded-medium flex items-center gap-2 border px-3 py-2"
                    role="alert"
                  >
                    <Icon
                      icon="heroicons:exclamation-triangle"
                      className="text-danger h-5 w-5 flex-shrink-0"
                    />
                    <span className="text-small">{error}</span>
                  </div>
                )}
                {showImageGallery && <ImageGallery images={images} />}
                {showMessageReferences && (
                  <MessageReferences references={references} />
                )}
                {showMessageActions && (
                  <MessageActions
                    content={content}
                    serverId={serverId}
                    message={message}
                  />
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  },
);

export default ChatMessage;
