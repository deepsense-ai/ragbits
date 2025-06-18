import type { TextAreaProps } from "@heroui/react";
import { forwardRef } from "react";
import { Textarea } from "@heroui/react";

const PromptInputText = forwardRef<HTMLTextAreaElement, TextAreaProps>(
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
