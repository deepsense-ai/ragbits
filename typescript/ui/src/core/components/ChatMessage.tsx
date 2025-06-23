import { forwardRef, useRef, useState } from "react";
import { Button, cn } from "@heroui/react";
import { Icon } from "@iconify/react/dist/iconify.js";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { MessageRole } from "ragbits-api-client-react";

import { ChatMessage as ChatMessageType } from "../../types/history.ts";
import { useThemeContext } from "../../contexts/ThemeContext/useThemeContext.ts";
import { Theme } from "../../contexts/ThemeContext/ThemeContext.ts";
import DelayedTooltip from "./DelayedTooltip";
import PluginWrapper from "../utils/plugins/PluginWrapper.tsx";
import { FeedbackFormPlugin } from "../../plugins/FeedbackPlugin/index.tsx";

export type ChatMessageProps = {
  classNames?: {
    wrapper?: string;
    innerWrapper?: string;
    content?: string;
  };
  chatMessage: ChatMessageType;
  isLoading: boolean;
};

const ChatMessage = forwardRef<HTMLDivElement, ChatMessageProps>(
  (
    {
      chatMessage: { serverId, content, role, references },
      classNames,
      isLoading,
    },
    ref,
  ) => {
    const rightAlign = role === MessageRole.USER;

    const [didAnimate, setDidAnimate] = useState(false);
    const [copyIcon, setCopyIcon] = useState("heroicons:clipboard");

    const copyIconTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const { theme } = useThemeContext();

    const onCopyClick = () => {
      navigator.clipboard.writeText(content);
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
              <div
                className={cn(
                  "prose whitespace-pre-line",
                  theme === Theme.DARK && "dark:prose-invert",
                  classNames?.content,
                )}
              >
                {content}
              </div>
            ) : (
              <>
                {content.length > 0 ? (
                  <Markdown
                    className={cn(
                      "markdown-container prose max-w-full",
                      theme === Theme.DARK && "dark:prose-invert",
                      classNames?.content,
                    )}
                    remarkPlugins={[remarkGfm]}
                  >
                    {content}
                  </Markdown>
                ) : (
                  <div className="flex items-center gap-2 text-default-500">
                    <Icon
                      icon="heroicons:arrow-path"
                      className="animate-spin"
                    />
                    <span>Thinking...</span>
                  </div>
                )}
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
                          <Icon icon={copyIcon} />
                        </Button>
                      </DelayedTooltip>

                      {serverId && (
                        <PluginWrapper
                          plugin={FeedbackFormPlugin}
                          component="FeedbackForm"
                          componentProps={{
                            messageServerId: serverId,
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
