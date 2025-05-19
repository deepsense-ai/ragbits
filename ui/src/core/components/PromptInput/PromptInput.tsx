import { Icon } from "@iconify/react";
import { Button } from "@heroui/button";
import { Form } from "@heroui/form";
import { cn } from "@heroui/theme";
import React, { useCallback } from "react";

import PromptInputText from "./PromptInputText";

interface PromptInputProps {
  isLoading: boolean;
  submit: () => void;
  message: string;
  setMessage: React.Dispatch<React.SetStateAction<string>>;
}

const PromptInput = ({
  message,
  setMessage,
  submit,
  isLoading,
}: PromptInputProps) => {
  const inputRef = React.useRef<HTMLTextAreaElement>(null);

  const handleSubmit = useCallback(() => {
    if (!prompt && !isLoading) return;

    submit();
    setMessage("");
    inputRef?.current?.focus();
  }, [setMessage, isLoading, submit]);

  const onSubmit = useCallback(
    (e: React.FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      handleSubmit();
    },
    [handleSubmit],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();

        handleSubmit();
      }
    },
    [handleSubmit],
  );

  return (
    <Form
      className="flex w-full flex-row items-start rounded-medium bg-default-100 dark:bg-default-100"
      validationBehavior="native"
      onSubmit={onSubmit}
    >
      <PromptInputText
        ref={inputRef}
        autoFocus
        classNames={{
          innerWrapper: "relative",
          input: "text-medium h-auto w-full",
          inputWrapper:
            "!bg-transparent shadow-none group-data-[focus-visible=true]:ring-0 group-data-[focus-visible=true]:ring-offset-0 pr-3 pl-[20px] pt-3 pb-4",
        }}
        maxRows={16}
        minRows={2}
        name="content"
        radius="lg"
        spellCheck={"false"}
        value={message}
        variant="flat"
        onKeyDown={handleKeyDown}
        onValueChange={setMessage}
      />
      <div className="flex flex-row items-center justify-end p-3">
        <Button
          isIconOnly
          color={!prompt ? "default" : "primary"}
          isDisabled={!prompt || isLoading}
          radius="full"
          size="sm"
          type="submit"
          variant="solid"
        >
          <Icon
            className={cn(
              "[&>path]:stroke-[2px]",
              !prompt ? "text-default-600" : "text-primary-foreground",
            )}
            icon="iconamoon:arrow-up-1-thin"
            width={20}
          />
        </Button>
      </div>
    </Form>
  );
};

export default PromptInput;
PromptInput.displayName = "PromptInput";
