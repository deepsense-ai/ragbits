import { forwardRef, useRef, useState } from "react";
import { Button, cn } from "@heroui/react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage } from "../../types/history.ts";
import { ConfigResponse, FormType, MessageRole } from "../../types/api";
import { Icon } from "@iconify/react";
import DelayedTooltip from "./DelayedTooltip";
import { useThemeContext } from "../../contexts/ThemeContext/useThemeContext.ts";
import { Theme } from "../../contexts/ThemeContext/ThemeContext.ts";

export type ChatMessageProps = {
  classNames?: string[];
  chatMessage: ChatMessage;
  onOpenFeedbackForm?: (id: string, name: FormType) => void;
  likeForm: ConfigResponse[FormType.LIKE];
  dislikeForm: ConfigResponse[FormType.DISLIKE];
};

const ChatMessage = forwardRef<HTMLDivElement, ChatMessageProps>(
  (
    {
      chatMessage: { serverId, content, role, references },
      onOpenFeedbackForm,
      classNames,
      likeForm,
      dislikeForm,
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
          ...(classNames ? classNames : []),
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
            )}
          >
            {rightAlign ? (
              <div
                className={cn(
                  "prose whitespace-pre-line",
                  theme === Theme.DARK && "dark:prose-invert",
                )}
              >
                {content}
              </div>
            ) : (
              <>
                <Markdown
                  className={cn(
                    "markdown-container prose max-w-full",
                    theme === Theme.DARK && "dark:prose-invert",
                  )}
                  remarkPlugins={[remarkGfm]}
                >
                  {content}
                </Markdown>
                {references && references.length > 0 && (
                  <div className="text-xs">
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
                  {onOpenFeedbackForm && (
                    <>
                      {likeForm !== undefined && (
                        <DelayedTooltip content="Like" placement="bottom">
                          <Button
                            isIconOnly
                            variant="ghost"
                            className="p-0"
                            aria-label="Like message"
                            onPress={() =>
                              onOpenFeedbackForm(serverId || "", FormType.LIKE)
                            }
                          >
                            <Icon icon="heroicons:hand-thumb-up" />
                          </Button>
                        </DelayedTooltip>
                      )}
                      {dislikeForm !== undefined && (
                        <DelayedTooltip content="Dislike" placement="bottom">
                          <Button
                            isIconOnly
                            variant="ghost"
                            className="p-0"
                            aria-label="Dislike message"
                            onPress={() =>
                              onOpenFeedbackForm(
                                serverId || "",
                                FormType.DISLIKE,
                              )
                            }
                          >
                            <Icon icon="heroicons:hand-thumb-down" />
                          </Button>
                        </DelayedTooltip>
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
