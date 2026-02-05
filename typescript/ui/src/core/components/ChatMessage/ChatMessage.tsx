import { forwardRef, useState } from "react";
import { cn } from "@heroui/react";
import { Icon } from "@iconify/react";

import MarkdownContent from "./MarkdownContent.tsx";
import LiveUpdates from "./LiveUpdates.tsx";
import ImageGallery from "./ImageGallery.tsx";
import MessageReferences from "./MessageReferences.tsx";
import MessageActions from "./MessageActions.tsx";
import LoadingIndicator from "./LoadingIndicator.tsx";
import ConfirmationDialogs from "./ConfirmationDialogs.tsx";
import {
  useConversationProperty,
  useHistoryActions,
  useMessage,
} from "../../stores/HistoryStore/selectors.ts";
import { MessageRole } from "@ragbits/api-client";
import TodoList from "../TodoList.tsx";
import { AnimatePresence, motion } from "framer-motion";
import { useRagbitsContext } from "@ragbits/api-client-react";

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
    const { sendSilentConfirmation } = useHistoryActions();
    const { client: ragbitsClient } = useRagbitsContext();

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
    const showLiveUpdates = liveUpdates && Object.keys(liveUpdates).length > 0;

    const showConfirmations =
      confirmationRequests && Object.keys(confirmationRequests).length > 0;

    const handleSingleConfirmation = async (confirmationId: string) => {
      try {
        await sendSilentConfirmation(
          messageId,
          confirmationId,
          true,
          ragbitsClient,
        );
      } catch (error) {
        console.error(error);
      }
    };

    const handleSingleSkip = async (confirmationId: string) => {
      try {
        await sendSilentConfirmation(
          messageId,
          confirmationId,
          false,
          ragbitsClient,
        );
      } catch (error) {
        console.error(error);
      }
    };

    const handleBulkConfirm = async (confirmationIds: string[]) => {
      // Build decisions for ALL confirmations (confirmed and declined)
      // This ensures the backend knows about all decisions, not just confirmed ones
      const allIds = confirmationRequests
        ? Object.keys(confirmationRequests)
        : [];
      const decisions = allIds.reduce(
        (acc, id) => ({ ...acc, [id]: confirmationIds.includes(id) }),
        {} as Record<string, boolean>,
      );

      try {
        await sendSilentConfirmation(
          messageId,
          allIds,
          decisions,
          ragbitsClient,
        );
      } catch (error) {
        console.error(error);
      }
    };

    const handleBulkSkip = async (confirmationIds: string[]) => {
      // Build decisions for ALL confirmations - mark all as skipped (false)
      const allIds = confirmationRequests
        ? Object.keys(confirmationRequests)
        : [];
      const decisions = allIds.reduce(
        (acc, id) => ({ ...acc, [id]: false }),
        {} as Record<string, boolean>,
      );

      try {
        await sendSilentConfirmation(
          messageId,
          confirmationIds,
          decisions,
          ragbitsClient,
        );
      } catch (error) {
        console.error(error);
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
                {showConfirmations && confirmationStates && (
                  <ConfirmationDialogs
                    confirmationRequests={confirmationRequests}
                    confirmationStates={confirmationStates}
                    onConfirm={handleSingleConfirmation}
                    onSkip={handleSingleSkip}
                    onBulkConfirm={handleBulkConfirm}
                    onBulkSkip={handleBulkSkip}
                    isLoading={isLoading}
                  />
                )}
                {message.hasConfirmationBreak && (
                  <div className="border-divider my-2 border-t" />
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
