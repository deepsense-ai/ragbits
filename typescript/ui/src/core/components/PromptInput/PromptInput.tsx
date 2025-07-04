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
} from "react";

import PromptInputText from "./PromptInputText";
import { TextAreaProps } from "@heroui/react";
import HorizontalActions from "./HorizontalActions";
import { useCaretLogicalLineDetection } from "../../utils/useTextAreaCaretDetection";
import { ChatMessage } from "../../../types/history";
import { MessageRole } from "@ragbits/api-client-react";
import PluginWrapper from "../../utils/plugins/PluginWrapper";
import { ChatOptionsPlugin } from "../../../plugins/ChatOptionsPlugin";

interface PromptInputProps {
  submit: (text: string, options?: Record<string, unknown>) => void;
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
  const [quickMessages, setQuickMessages] = useState<string[]>([]);
  const [chatOptions, setChatOptions] = useState<Record<string, unknown>>({});
  const textAreaRef = useRef<HTMLTextAreaElement>(null);
  const { isCaretInFirstLine, isCaretInLastLine } =
    useCaretLogicalLineDetection();
  const quickMessageIndex = useRef(Math.max(quickMessages.length - 1, 0));

  const setQuickMessage = useCallback(() => {
    const quickMessage = quickMessages[quickMessageIndex.current];

    setMessage(quickMessage);
  }, [quickMessages]);

  const onArrowUp = useCallback(() => {
    quickMessageIndex.current = Math.max(quickMessageIndex.current - 1, 0);
    setQuickMessage();
  }, [setQuickMessage]);

  const onArrowDown = useCallback(() => {
    quickMessageIndex.current = Math.min(
      quickMessages.length - 1,
      quickMessageIndex.current + 1,
    );
    setQuickMessage();
  }, [quickMessages, setQuickMessage]);

  const handleSubmit = useCallback(
    (text?: string) => {
      if (!message && !isLoading && !text) return;

      submit(text ?? message, chatOptions);
      setQuickMessages((quickMessages) => {
        const newQuickMessages = quickMessages.slice(0, -1);
        newQuickMessages.push(text ?? message);
        return newQuickMessages;
      });
      setMessage("");
      textAreaRef?.current?.focus();
    },
    [isLoading, submit, message, chatOptions],
  );

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

      if (e.key === "ArrowUp") {
        if (!isCaretInFirstLine(textAreaRef.current)) {
          return;
        }

        e.preventDefault();
        onArrowUp();
      }

      if (e.key === "ArrowDown") {
        if (!isCaretInLastLine(textAreaRef.current)) {
          return;
        }

        e.preventDefault();
        onArrowDown();
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

  const handleValueChange = useCallback((value: string) => {
    setQuickMessages((quickMessages) => {
      const newQuickMessages = [...quickMessages];
      newQuickMessages[quickMessageIndex.current] = value;

      return newQuickMessages;
    });
    setMessage(value);
  }, []);

  useEffect(() => {
    const newQuickMessages = (history ?? [])
      .filter((m) => m.role === MessageRole.USER)
      .map((m) => m.content);

    if (quickMessages.length - 1 === newQuickMessages.length) {
      return;
    }

    newQuickMessages.push("");
    quickMessageIndex.current = Math.max(newQuickMessages.length - 1, 0);
    setQuickMessages(newQuickMessages);
  }, [history, quickMessages.length]);

  return (
    <div className="rounded-medium">
      <HorizontalActions
        isVisible={!!followupMessages}
        actions={followupMessages ?? []}
        sendMessage={(text: string) => handleSubmit(text)}
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
          onValueChange={handleValueChange}
          {...inputProps}
        />
        <div className="flex items-center gap-2">
          <PluginWrapper
            plugin={ChatOptionsPlugin}
            component="ChatOptionsForm"
            componentProps={{
              chatOptions,
              onOptionsChange: (data: Record<string, unknown>) => {
                setChatOptions(data);
              },
            }}
            skeletonSize={{
              width: "40px",
              height: "40px",
            }}
          />
          <Button
            isIconOnly
            aria-label={
              isLoading ? "Stop answering" : "Send message to the chat"
            }
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
        </div>
      </Form>
    </div>
  );
};

export default PromptInput;
