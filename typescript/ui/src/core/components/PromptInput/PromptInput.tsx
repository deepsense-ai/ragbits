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
} from "react";

import PromptInputText from "./PromptInputText";
import { TextAreaProps } from "@heroui/react";
import HorizontalActions from "./HorizontalActions";

interface PromptInputProps {
  submit: (text: string) => void;
  stopAnswering: () => void;
  isLoading: boolean;
  followupMessages?: string[] | null;
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
}: PromptInputProps) => {
  const [message, setMessage] = useState("");
  const textAreaRef = useRef<HTMLTextAreaElement>(null);

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
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();

        handleSubmit();
      }
    },
    [handleSubmit],
  );

  const handleStopAnswering = useCallback(() => {
    stopAnswering();
    textAreaRef?.current?.focus();
  }, [stopAnswering]);

  return (
    <div className="rounded-medium">
      <HorizontalActions
        isVisible={!!followupMessages}
        actions={followupMessages ?? []}
        sendMessage={submit}
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
            input: "text-medium",
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
