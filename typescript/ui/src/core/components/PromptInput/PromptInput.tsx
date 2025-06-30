import { Icon } from "@iconify/react";
import { Button, ButtonProps } from "@heroui/button";
import { Form, FormProps } from "@heroui/form";
import { cn } from "@heroui/theme";
import {
  KeyboardEvent,
  FormEvent,
  useCallback,
  useRef,
  ReactNode,
  useState,
  useEffect,
  useMemo,
} from "react";

import PromptInputText from "./PromptInputText";
import { TextAreaProps } from "@heroui/react";
import HorizontalActions from "./HorizontalActions";
import { useCaretLogicalLineDetection } from "../../utils/useTextAreaCaretDetection";
import { ChatMessage } from "../../../types/history";
import { MessageRole } from "@ragbits/api-client-react";

interface PromptInputProps {
  submit: (text: string) => void;
  stopAnswering: () => void;
  onArrowUp?: (isFirstLine: boolean) => void;
  onArrowDown?: (isLastLine: boolean) => void;
  isLoading: boolean;
  followupMessages?: string[] | null;
  history?: ChatMessage[];
  formProps?: FormProps;
  inputProps?: TextAreaProps;
  sendButtonProps?: ButtonProps;
  customSendIcon?: ReactNode;
  customStopIcon?: ReactNode;
}

const PromptInput = ({
  followupMessages,
  submit,
  stopAnswering,
  isLoading,
  formProps,
  inputProps,
  sendButtonProps,
  customSendIcon,
  customStopIcon,
  history,
}: PromptInputProps) => {
  const [message, setMessage] = useState("");
  const textAreaRef = useRef<HTMLTextAreaElement>(null);
  const { isCaretInFirstLine, isCaretInLastLine } =
    useCaretLogicalLineDetection();
  const historyLength = useMemo(() => history?.length ?? 0, [history?.length]);
  const quickMessageIndex = useRef(Math.max(historyLength - 2, 0));

  const setQuickMessage = useCallback(() => {
    if (!history) {
      return;
    }

    const quickMessage = history[quickMessageIndex.current];
    if (!quickMessage || quickMessage.role !== MessageRole.USER) {
      return;
    }

    setMessage(quickMessage.content);
  }, [history]);

  const onArrowUp = useCallback(
    (isFirst: boolean) => {
      if (!isFirst) {
        return;
      }

      quickMessageIndex.current = Math.max(quickMessageIndex.current - 2, 0);
      setQuickMessage();
    },
    [setQuickMessage],
  );

  const onArrowDown = useCallback(
    (isLast: boolean) => {
      if (!isLast) {
        return;
      }

      quickMessageIndex.current = Math.min(
        Math.max(historyLength - 2, 0),
        quickMessageIndex.current + 2,
      );
      setQuickMessage();
    },
    [historyLength, setQuickMessage],
  );

  const handleSubmit = useCallback(() => {
    if (!message && !isLoading) return;

    submit(message);
    setMessage("");
    textAreaRef?.current?.focus();
  }, [isLoading, submit, message]);

  const onSubmit = useCallback(
    (e: FormEvent<HTMLFormElement>) => {
      e.preventDefault();

      handleSubmit();
    },
    [handleSubmit],
  );

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      if (!textAreaRef.current) return;

      if (e.key === "ArrowUp" && onArrowUp) {
        onArrowUp(isCaretInFirstLine(textAreaRef.current));
      }

      if (e.key === "ArrowDown" && onArrowDown) {
        onArrowDown(isCaretInLastLine(textAreaRef.current));
      }

      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();

        handleSubmit();
      }
    },
    [
      handleSubmit,
      isCaretInFirstLine,
      isCaretInLastLine,
      onArrowDown,
      onArrowUp,
    ],
  );

  const handleStopAnswering = useCallback(() => {
    stopAnswering();
    textAreaRef?.current?.focus();
  }, [stopAnswering]);

  const sendFollowupMessage = useCallback(
    (text: string) => {
      setMessage("");
      submit(text);
    },
    [submit],
  );

  useEffect(() => {
    quickMessageIndex.current = Math.max(0, historyLength);
  }, [historyLength]);

  return (
    <div className="rounded-medium">
      <HorizontalActions
        isVisible={!!followupMessages}
        actions={followupMessages ?? []}
        sendMessage={sendFollowupMessage}
      />

      <Form
        className="flex w-full flex-row items-center rounded-medium bg-default-100 pl-0 pr-2 dark:bg-default-100"
        validationBehavior="native"
        onSubmit={onSubmit}
        {...formProps}
      >
        <PromptInputText
          ref={textAreaRef}
          aria-label="Message to the chat"
          classNames={{
            input: "text-medium text-default-foreground",
            inputWrapper:
              "!bg-transparent shadow-none group-data-[focus-visible=true]:ring-0 group-data-[focus-visible=true]:ring-offset-0 py-4",
          }}
          name="message"
          placeholder="Enter a message here"
          autoFocus
          maxRows={16}
          minRows={1}
          value={message}
          onKeyDown={handleKeyDown}
          onValueChange={setMessage}
          {...inputProps}
        />
        <Button
          isIconOnly
          aria-label={isLoading ? "Stop answering" : "Send message to the chat"}
          color={!isLoading && !message ? "default" : "primary"}
          isDisabled={!isLoading && !message}
          radius="full"
          size="sm"
          type={isLoading ? "button" : "submit"}
          onPress={isLoading ? handleStopAnswering : undefined}
          {...sendButtonProps}
        >
          {!isLoading &&
            (customSendIcon ?? (
              <Icon
                className={cn(
                  !message ? "text-default-600" : "text-primary-foreground",
                )}
                icon="heroicons:arrow-up"
                width={20}
              />
            ))}
          {isLoading &&
            (customStopIcon ?? (
              <Icon
                className="text-primary-foreground"
                icon="heroicons:stop"
                width={20}
              />
            ))}
        </Button>
      </Form>
    </div>
  );
};

export default PromptInput;
