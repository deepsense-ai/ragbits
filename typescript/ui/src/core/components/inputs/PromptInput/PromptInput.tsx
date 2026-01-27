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
  ChangeEvent,
  useEffect,
} from "react";

import { useRagbitsCall } from "@ragbits/api-client-react";

import PromptInputText from "./PromptInputText";
import { TextAreaProps } from "@heroui/react";
import HorizontalActions from "./HorizontalActions";
import { useCaretLogicalLineDetection } from "../../../utils/useTextAreaCaretDetection";
import { ChatMessage } from "../../../../types/history";
import { MessageRole } from "@ragbits/api-client";

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
  pluginSlots?: {
    "chat-options"?: ReactNode;
  };
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
  pluginSlots = {},
}: PromptInputProps) => {
  const [message, setMessage] = useState("");
  const [quickMessages, setQuickMessages] = useState<string[]>([]);
  const formRef = useRef<HTMLFormElement>(null);
  const textAreaRef = useRef<HTMLTextAreaElement>(null);
  const { isCaretInFirstLine, isCaretInLastLine } =
    useCaretLogicalLineDetection();
  const quickMessageIndex = useRef(Math.max(quickMessages.length - 1, 0));
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { call: uploadFile, isLoading: isUploading } =
    useRagbitsCall("/api/upload");

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

  const handleValueChange = useCallback((value: string) => {
    setQuickMessages((quickMessages) => {
      const newQuickMessages = [...quickMessages];
      newQuickMessages[quickMessageIndex.current] = value;

      return newQuickMessages;
    });
    setMessage(value);
  }, []);

  const handleFileClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const formData = new FormData();
      formData.append("file", file);
      await uploadFile({
        method: "POST",
        body: formData,
      });
    } catch (err) {
      console.error("Upload failed", err);
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

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

      <Form
        className="rounded-medium bg-default-100 dark:bg-default-100 flex w-full flex-row items-center pr-2 pl-0"
        validationBehavior="native"
        onSubmit={onSubmit}
        ref={formRef}
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
          onValueChange={handleValueChange}
          data-testid="prompt-input-input"
          data-value={message}
          isDisabled={isDisabled}
          {...inputProps}
        />
        <div className="flex items-center gap-2">
          <input
            type="file"
            ref={fileInputRef}
            className="hidden"
            onChange={handleFileChange}
          />
          <Button
            isIconOnly
            aria-label="Upload file"
            variant="light"
            radius="full"
            size="sm"
            onPress={handleFileClick}
            isLoading={isUploading}
            isDisabled={isDisabled || isLoading}
          >
            <Icon
              className="text-default-500"
              icon="heroicons:paper-clip"
              width={20}
            />
          </Button>
          {pluginSlots["chat-options"]}
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
      </Form>
    </div>
  );
};

export default PromptInput;
