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
} from "react";

import PromptInputText from "./PromptInputText";
import { TextAreaProps } from "@heroui/react";

interface PromptInputProps {
  isLoading: boolean;
  submit: () => void;
  message: string;
  setMessage: (message: string) => void;
  formProps?: FormProps;
  inputProps?: TextAreaProps;
  sendButtonProps?: ButtonProps;
  customSendIcon?: ReactNode;
}

const PromptInput = ({
  message,
  setMessage,
  submit,
  isLoading,
  formProps,
  inputProps,
  sendButtonProps,
  customSendIcon,
}: PromptInputProps) => {
  const textAreaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = useCallback(() => {
    if (!message && !isLoading) return;

    submit();
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

  return (
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
        aria-label="Send message to the chat"
        color={!message ? "default" : "primary"}
        isDisabled={!message || isLoading}
        radius="full"
        size="sm"
        type="submit"
        {...sendButtonProps}
      >
        {customSendIcon ?? (
          <Icon
            className={cn(
              !message ? "text-default-600" : "text-primary-foreground",
            )}
            icon="heroicons:arrow-up"
            width={20}
          />
        )}
      </Button>
    </Form>
  );
};

export default PromptInput;
