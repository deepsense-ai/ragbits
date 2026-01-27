import { strToU8, zlibSync, strFromU8, unzlibSync } from "fflate";
import {
  Button,
  Modal,
  ModalBody,
  ModalContent,
  ModalHeader,
  useDisclosure,
} from "@heroui/react";
import { Icon } from "@iconify/react";
import DelayedTooltip from "../../../core/components/DelayedTooltip";
import { useState, useRef, useEffect } from "react";
import { toJSONSafe } from "../../../core/utils/json";
import { Conversation } from "../../../core/types/history";
import { useHistoryPrimitives } from "../../../core/stores/HistoryStore/selectors";
import { useHistoryStore } from "../../../core/stores/HistoryStore/useHistoryStore";

const DEFAULT_ICON = "heroicons:share";
const SUCCESS_ICON = "heroicons:check";
const SHARE_TAG = "RAGBITS-STATE";
const SHARE_START_TAG = `<${SHARE_TAG}>`;
const SHARE_END_TAG = `</${SHARE_TAG}>`;

interface SharedState {
  history: Conversation["history"];
  followupMessages: Conversation["followupMessages"];
  chatOptions: Conversation["chatOptions"];
  serverState: Conversation["serverState"];
  conversationId: Conversation["conversationId"];
}

function isSharedState(value: unknown): value is SharedState {
  if (typeof value !== "object" || value === null) return false;

  const state = value as Partial<SharedState>;
  if (typeof state.history !== "object") return false;
  if ("followupMessages" in state && typeof state.followupMessages !== "object")
    return false;
  if ("chatOptions" in state && typeof state.chatOptions !== "object")
    return false;
  if ("serverState" in state && typeof state.serverState !== "object")
    return false;
  if (
    "conversationId" in state &&
    typeof state.conversationId !== "string" &&
    typeof state.conversationId !== "object"
  )
    return false;

  return true;
}

export default function ShareButton() {
  const { restore } = useHistoryPrimitives();
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [icon, setIcon] = useState(DEFAULT_ICON);
  const iconTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { getCurrentConversation } = useHistoryStore((s) => s.primitives);

  const onShare = () => {
    const {
      chatOptions,
      history,
      serverState,
      conversationId,
      followupMessages,
    } = getCurrentConversation();

    const state = toJSONSafe({
      chatOptions,
      history: history,
      serverState,
      conversationId,
      followupMessages,
    });
    const buffer = strToU8(
      `${SHARE_START_TAG}${JSON.stringify(state)}${SHARE_END_TAG}`,
    );
    const encodedState = btoa(strFromU8(zlibSync(buffer, { level: 9 }), true));

    navigator.clipboard.writeText(encodedState);
    setIcon(SUCCESS_ICON);
    onClose();

    if (iconTimerRef.current) {
      clearTimeout(iconTimerRef.current);
    }
    iconTimerRef.current = setTimeout(() => {
      setIcon(DEFAULT_ICON);
    }, 2000);
  };

  const onOpenChange = () => {
    onClose();
  };

  useEffect(() => {
    const decode = (e: ClipboardEvent) => {
      if (!e.clipboardData) {
        return;
      }

      const types = e.clipboardData.types;
      if (!types.includes("text/plain") && !types.includes("text")) {
        return;
      }

      const pastedText =
        e.clipboardData.getData("text/plain") ??
        e.clipboardData.getData("text");
      try {
        const pastedBinary = atob(pastedText);

        if (!pastedBinary.startsWith("\x78\xDA")) {
          // No zlib header, ignore
          return;
        }

        // Try to decode and check for the existence of the state tags
        const parsedText = strFromU8(unzlibSync(strToU8(pastedBinary, true)));
        if (
          !parsedText.startsWith(SHARE_START_TAG) ||
          !parsedText.endsWith(SHARE_END_TAG)
        ) {
          return;
        }

        e.preventDefault();
        e.stopPropagation();

        const stateText = parsedText.slice(
          SHARE_START_TAG.length,
          -SHARE_END_TAG.length,
        );
        const parsedState = JSON.parse(stateText);
        if (!isSharedState(parsedState)) {
          return;
        }

        restore(
          parsedState.history,
          parsedState.followupMessages,
          parsedState.chatOptions,
          parsedState.serverState,
          parsedState.conversationId,
        );
      } catch (e) {
        console.error("Couldn't parse pasted string as valid Ragbits state", e);
      }
    };

    window.addEventListener("paste", decode);

    return () => {
      window.removeEventListener("paste", decode);
    };
  });

  return (
    <>
      <DelayedTooltip content="Share conversation" placement="bottom">
        <Button
          isIconOnly
          variant="ghost"
          className="p-0"
          aria-label="Share conversation"
          onPress={onOpen}
        >
          <Icon icon={icon} />
        </Button>
      </DelayedTooltip>

      <Modal isOpen={isOpen} onOpenChange={onOpenChange}>
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader className="text-default-900 flex flex-col gap-1">
                Share conversation
              </ModalHeader>
              <ModalBody>
                <div className="flex flex-col gap-4">
                  <p className="text-medium text-default-500">
                    You are about to copy a code that allows sharing and storing
                    your current app state. Once copied, you can paste this code
                    anywhere on the site to instantly return to this exact
                    setup. It’s a quick way to save your progress or share it
                    with others.
                  </p>
                  <div className="flex justify-end gap-4 py-4">
                    <Button
                      color="danger"
                      variant="light"
                      onPress={onClose}
                      aria-label="Close share modal"
                    >
                      Cancel
                    </Button>
                    <Button
                      color="primary"
                      onPress={onShare}
                      aria-label="Copy to clipboard to share the conversation"
                    >
                      Copy to clipboard
                    </Button>
                  </div>
                </div>
              </ModalBody>
            </>
          )}
        </ModalContent>
      </Modal>
    </>
  );
}
