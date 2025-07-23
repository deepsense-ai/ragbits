import { ComponentProps } from "react";
import PromptInput from "./PromptInput/PromptInput";
import { useMessages } from "../../stores/HistoryStore/selectors";

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
