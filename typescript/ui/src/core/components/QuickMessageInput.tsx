import { useMessages } from "../stores/historyStore";
import PromptInput, { PromptInputProps } from "./PromptInput/PromptInput";

type QuickMessageInputProps = Omit<PromptInputProps, "history">;

export default function QuickMessageInput({
  ...props
}: QuickMessageInputProps) {
  const messages = useMessages();

  return <PromptInput {...props} history={messages} />;
}
