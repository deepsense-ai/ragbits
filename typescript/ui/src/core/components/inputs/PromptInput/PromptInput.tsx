import { Icon } from "@iconify/react";
import { Button, ButtonProps } from "@heroui/button";
import { Form, FormProps } from "@heroui/form";
import { cn } from "@heroui/theme";
import {
  KeyboardEvent,
  ClipboardEvent,
  DragEvent,
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
import { useCaretLogicalLineDetection } from "../../../utils/useTextAreaCaretDetection";
import { Slot } from "../../Slot";
import { MessageRole } from "@ragbits/api-client";
import { ChatMessage } from "../../../types/history";
import { dispatchDroppedFiles } from "../../../utils/fileHandlers";

export interface PromptInputProps {
  submit: (text: string) => void;
  stopAnswering: () => void;
  isLoading: boolean;
  followupMessages?: string[] | null;
  history?: ChatMessage[];
  formProps?: FormProps;
  inputProps?: TextAreaProps;
  sendButtonProps?: ButtonProps;
  customSendIcon?: ReactNode;
  customStopIcon?: ReactNode;
  isDisabled?: boolean;
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
  isDisabled = false,
}: PromptInputProps) => {
  const [message, setMessage] = useState("");
  const [quickMessages, setQuickMessages] = useState<string[]>([]);
  const formRef = useRef<HTMLFormElement>(null);
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
      if (!message && !text) return;
      if (isDisabled) return; // Prevent submission when disabled
      stopAnswering();

      submit(text ?? message);
      setQuickMessages((quickMessages) => {
        const newQuickMessages = quickMessages.slice(0, -1);
        newQuickMessages.push(text ?? message);
        return newQuickMessages;
      });
      setMessage("");
      textAreaRef?.current?.focus();
    },
    [message, stopAnswering, submit, isDisabled],
  );

  const onSubmit = useCallback(
    (e: FormEvent<HTMLFormElement>) => {
      if (e.target !== formRef.current) {
        return;
      }

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

  const [isDragOver, setIsDragOver] = useState(false);

  const handleDragOver = useCallback((e: DragEvent<HTMLDivElement>) => {
    if (!Array.from(e.dataTransfer.types).includes("Files")) return;
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: DragEvent<HTMLDivElement>) => {
    if (e.currentTarget.contains(e.relatedTarget as Node | null)) return;
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: DragEvent<HTMLDivElement>) => {
    const files = Array.from(e.dataTransfer.files);
    if (files.length === 0) return;
    e.preventDefault();
    setIsDragOver(false);
    dispatchDroppedFiles(files);
  }, []);

  const handlePaste = useCallback((e: ClipboardEvent<HTMLInputElement>) => {
    const files = Array.from(e.clipboardData.files);
    if (files.length === 0) return;
    e.preventDefault();
    dispatchDroppedFiles(files);
  }, []);

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
      .filter((m) => m.role === MessageRole.User)
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

      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
      <Form
        className={cn(
          "rounded-medium bg-default-100 dark:bg-default-100 flex w-full flex-col items-stretch pr-2 pl-0",
          isDragOver && "ring-primary ring-2",
        )}
        validationBehavior="native"
        onSubmit={onSubmit}
        ref={formRef}
        {...formProps}
      >
        <Slot
          name="prompt.attachments"
          props={{ isInputDisabled: isLoading || isDisabled }}
        />
        <div className="flex flex-row items-center">
        <PromptInputText
          ref={textAreaRef}
          aria-label="Message to the chat"
          classNames={{
            input: "text-medium text-default-foreground",
            inputWrapper:
              "!bg-transparent shadow-none group-data-[focus-visible=true]:ring-0 group-data-[focus-visible=true]:ring-offset-0 py-4",
          }}
          name="message"
          placeholder={
            isDisabled
              ? "Please respond to pending confirmation..."
              : "Enter a message here"
          }
          autoFocus
          maxRows={16}
          minRows={1}
          value={message}
          onKeyDown={handleKeyDown}
          onPaste={handlePaste}
          onValueChange={handleValueChange}
          data-testid="prompt-input-input"
          data-value={message}
          isDisabled={isDisabled}
          {...inputProps}
        />
        <div className="flex items-center gap-2">
          <Slot
            name="prompt.beforeSend"
            skeletonSize={{ width: "40px", height: "40px" }}
            props={{ isInputDisabled: isLoading || isDisabled }}
          />
          <Button
            isIconOnly
            aria-label={
              isLoading ? "Stop answering" : "Send message to the chat"
            }
            color={!isLoading && !message ? "default" : "primary"}
            isDisabled={!isLoading && (!message || isDisabled)}
            radius="full"
            size="sm"
            type={isLoading ? "button" : "submit"}
            onPress={isLoading ? handleStopAnswering : undefined}
            data-testid="send-message"
            {...sendButtonProps}
          >
            <>
              {!isLoading &&
                (customSendIcon ?? (
                  <Icon
                    className={cn(
                      !message ? "text-default-600" : "text-primary-foreground",
                    )}
                    icon="heroicons:arrow-up"
                    data-testid="prompt-input-send-icon"
                    width={20}
                  />
                ))}
              {isLoading &&
                (customStopIcon ?? (
                  <Icon
                    className="text-primary-foreground"
                    icon="heroicons:stop"
                    data-testid="prompt-input-stop-icon"
                    width={20}
                  />
                ))}
            </>
          </Button>
        </div>
        </div>
      </Form>
      </div>
    </div>
  );
};

export default PromptInput;
