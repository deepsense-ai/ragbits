import { useRef, useState } from "react";
import { Button } from "@heroui/react";
import { Icon } from "@iconify/react";

import DelayedTooltip from "../DelayedTooltip.tsx";
import { Slot } from "../Slot.tsx";
import { ChatMessage } from "../../types/history.ts";

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
      <Slot
        name="message.actions"
        props={{ message, content, serverId }}
        skeletonSize={{ width: "88px", height: "40px" }}
      />

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
    </div>
  );
};

export default MessageActions;
