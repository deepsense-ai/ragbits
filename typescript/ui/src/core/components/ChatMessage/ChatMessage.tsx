import { forwardRef, useState } from "react";
import { cn } from "@heroui/react";

import MarkdownContent from "./MarkdownContent.tsx";
import LiveUpdates from "./LiveUpdates.tsx";
import ImageGallery from "./ImageGallery.tsx";
import MessageReferences from "./MessageReferences.tsx";
import MessageActions from "./MessageActions.tsx";
import LoadingIndicator from "./LoadingIndicator.tsx";
import ConfirmationDialog from "./ConfirmationDialog.tsx";
import {
  useConversationProperty,
  useMessage,
} from "../../stores/HistoryStore/selectors.ts";
import { MessageRole } from "@ragbits/api-client";
import TodoList from "../TodoList.tsx";
import { AnimatePresence, motion } from "framer-motion";
import { useHistoryStore } from "../../stores/HistoryStore/useHistoryStore.ts";

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
    const conversation = useHistoryStore((s) =>
      s.primitives.getCurrentConversation(),
    );

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
      confirmationRequest,
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
    const showConfirmation = !!confirmationRequest;

    const handleConfirmation = async (confirmed: boolean) => {
      if (!confirmationRequest) return;

      try {
        await fetch("/api/confirm", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            confirmation_id: confirmationRequest.confirmation_id,
            confirmed,
          }),
        });

        // Clear the confirmation request from the message after responding
        // Note: Direct mutation here - zustand will see the change on next render
        conversation.history[messageId].confirmationRequest = undefined;
      } catch (error) {
        console.error("Failed to send confirmation:", error);
      }
    };

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
                {message.tasks && message.tasks.length > 0 && (
                  <AnimatePresence>
                    <motion.div
                      key={`${message.id}-execution-plan`}
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.3, ease: "easeOut" }}
                      className="rounded-medium text-large text-default-900 border-default flex w-fit flex-col gap-2 border p-4"
                    >
                      <p>Execution plan</p>
                      <TodoList tasks={message.tasks} />
                    </motion.div>
                  </AnimatePresence>
                )}
                {showConfirmation && (
                  <ConfirmationDialog
                    confirmationRequest={confirmationRequest}
                    onConfirm={() => handleConfirmation(true)}
                    onSkip={() => handleConfirmation(false)}
                  />
                )}
                <MarkdownContent
                  content={content}
                  classNames={classNames?.content}
                />
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
