import { forwardRef, useRef, useState } from "react";
import { Button, cn } from "@heroui/react";
import { Icon } from "@iconify/react/dist/iconify.js";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { MessageRole } from "@ragbits/api-client-react";

import DelayedTooltip from "./DelayedTooltip.tsx";
import PluginWrapper from "../utils/plugins/PluginWrapper.tsx";
import { FeedbackFormPlugin } from "../../plugins/FeedbackPlugin/index.tsx";
import LiveUpdates from "./LiveUpdates.tsx";
import { useHistoryStore, useMessage } from "../stores/historyStore.ts";

export type ChatMessageProps = {
  classNames?: {
    wrapper?: string;
    innerWrapper?: string;
    content?: string;
    liveUpdates?: string;
  };
  messageId: string;
};

const MarkdownContent = ({
  content,
  classNames,
}: {
  content: string;
  classNames?: string;
}) => {
  return (
    <Markdown
      className={cn(
        "markdown-container prose max-w-full dark:prose-invert",
        classNames,
      )}
      remarkPlugins={[remarkGfm]}
      components={{
        pre: ({ children }) => (
          <pre className="max-w-full overflow-auto rounded bg-gray-200 p-2 font-mono font-normal text-gray-800 dark:bg-gray-800 dark:text-gray-200">
            {children}
          </pre>
        ),
        code: ({ children }) => (
          <code className="rounded bg-gray-200 px-2 py-1 font-mono font-normal text-gray-800 dark:bg-gray-800 dark:text-gray-200">
            {children}
          </code>
        ),
      }}
    >
      {content}
    </Markdown>
  );
};

const ChatMessage = forwardRef<HTMLDivElement, ChatMessageProps>(
  ({ messageId, classNames }, ref) => {
    const lastMessageId = useHistoryStore((s) => s.lastMessageId);
    const isHistoryLoading = useHistoryStore((s) => s.isLoading);
    const message = useMessage(messageId);
    if (!message) {
      throw new Error("Tried to render non-existent message");
    }

    const { serverId, content, role, references, liveUpdates } = message;
    const rightAlign = role === MessageRole.USER;
    const isLoading =
      isHistoryLoading &&
      role === MessageRole.ASSISTANT &&
      messageId === lastMessageId;

    const [didAnimate, setDidAnimate] = useState(false);
    const [copyIcon, setCopyIcon] = useState("heroicons:clipboard");

    const copyIconTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    const onCopyClick = async () => {
      await navigator.clipboard.writeText(content);
      setCopyIcon("heroicons:check");
      if (copyIconTimerRef.current) {
        clearTimeout(copyIconTimerRef.current);
      }
      copyIconTimerRef.current = setTimeout(() => {
        setCopyIcon("heroicons:clipboard");
      }, 2000);
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
              <>
                <div className="flex items-center gap-2 text-default-500">
                  <LiveUpdates
                    isLoading={isLoading}
                    liveUpdates={liveUpdates}
                    classNames={{ liveUpdates: classNames?.liveUpdates }}
                  />
                  {isLoading && !liveUpdates && (
                    <>
                      <Icon
                        icon="heroicons:arrow-path"
                        className="animate-spin"
                      />
                      <span>
                        {content.length > 0 ? "Generating..." : "Thinking..."}
                      </span>
                    </>
                  )}
                </div>
                <MarkdownContent
                  content={content}
                  classNames={classNames?.content}
                />
                {references && references.length > 0 && !isLoading && (
                  <div className="text-xs italic text-default-500">
                    <ul className="list-disc pl-4">
                      {references.map((reference, index) => (
                        <li key={index}>
                          <a
                            href={reference.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hover:underline"
                          >
                            {reference.title}
                          </a>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                <div className="mt-2 flex items-center gap-2">
                  {!isLoading && (
                    <>
                      <DelayedTooltip content="Copy" placement="bottom">
                        <Button
                          isIconOnly
                          variant="ghost"
                          className="p-0"
                          aria-label="Copy message"
                          onPress={onCopyClick}
                        >
                          <Icon
                            icon={copyIcon}
                            data-testid="chat-message-copy-icon"
                            data-icon={copyIcon}
                          />
                        </Button>
                      </DelayedTooltip>

                      {serverId && (
                        <PluginWrapper
                          plugin={FeedbackFormPlugin}
                          component="FeedbackForm"
                          componentProps={{
                            message,
                          }}
                          skeletonSize={{
                            width: "88px",
                            height: "40px",
                          }}
                        />
                      )}
                    </>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    );
  },
);

ChatMessage.displayName = "ChatMessage";

export default ChatMessage;
