import { Icon } from "@iconify/react";
import { Button } from "@heroui/button";
import { Form } from "@heroui/form";
import { cn } from "@heroui/theme";
import { KeyboardEvent, FormEvent, useCallback, useRef } from "react";

import PromptInputText from "./PromptInputText";

interface PromptInputProps {
  isLoading: boolean;
  submit: () => void;
  message: string;
  setMessage: (message: string) => void;
}

const PromptInput = ({
  message,
  setMessage,
  submit,
  isLoading,
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
    >
      <PromptInputText
        ref={textAreaRef}
        aria-label="Message"
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
      />
      <Button
        isIconOnly
        color={!message ? "default" : "primary"}
        isDisabled={!message || isLoading}
        radius="full"
        size="sm"
        type="submit"
      >
        <Icon
          className={cn(
            "[&>path]:stroke-[2px]",
            !message ? "text-default-600" : "text-primary-foreground",
          )}
          icon="iconamoon:arrow-up-1-thin"
          width={20}
        />
      </Button>
    </Form>
  );
};

export default PromptInput;
