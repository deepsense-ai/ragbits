import type { TextAreaProps } from "@heroui/react";
import { forwardRef } from "react";
import { Textarea } from "@heroui/react";

interface PromptInputTextProps extends TextAreaProps {}

const PromptInputText = forwardRef<HTMLTextAreaElement, PromptInputTextProps>(
  ({ classNames = {}, ...props }, ref) => {
    return (
      <Textarea
        ref={ref}
        className="min-h-[50px]"
        classNames={classNames}
        {...props}
      />
    );
  },
);

export default PromptInputText;
