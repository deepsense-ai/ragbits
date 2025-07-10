import { ComponentProps } from "react";
import { useMessages } from "../../stores/historyStore";
import PromptInput from "./PromptInput/PromptInput";

type QuickMessageInputProps = Omit<
  ComponentProps<typeof PromptInput>,
  "history"
>;

export default function QuickMessageInput({
  ...props
}: QuickMessageInputProps) {
  const messages = useMessages();

  return <PromptInput {...props} history={messages} />;
}
