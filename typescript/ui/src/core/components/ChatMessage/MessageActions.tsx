import { useRef, useState } from "react";
import { Button } from "@heroui/react";
import { Icon } from "@iconify/react";

import DelayedTooltip from "../DelayedTooltip.tsx";
import PluginWrapper from "../../utils/plugins/PluginWrapper.tsx";
import { FeedbackFormPlugin } from "../../../plugins/FeedbackPlugin/index.tsx";
import { ChatMessage } from "../../types/history.ts";
import { UsagePlugin } from "../../../plugins/UsagePlugin/index.tsx";

type MessageActionsProps = {
  content: string;
  serverId?: string;
  message: ChatMessage;
};

const MessageActions = ({
  content,
  serverId,
  message,
}: MessageActionsProps) => {
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
    <div className="flex items-center gap-2">
      {message.usage && Object.keys(message.usage).length >= 1 && (
        <PluginWrapper
          plugin={UsagePlugin}
          component="UsageButton"
          componentProps={{
            usage: message.usage,
          }}
          skeletonSize={{
            width: "88px",
            height: "40px",
          }}
        />
      )}

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
    </div>
  );
};

export default MessageActions;
