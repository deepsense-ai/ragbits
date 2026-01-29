import { useShallow } from "zustand/shallow";
import { Conversation } from "../../types/history";
import { useHistoryStore } from "./useHistoryStore";

export const useHistoryActions = () => useHistoryStore((s) => s.actions);
export const useHistoryPrimitives = () => useHistoryStore((s) => s.primitives);
export const useHistoryComputed = () => useHistoryStore((s) => s.computed);
export const useConversationProperty = <T>(
  selector: (s: Conversation) => T,
): T =>
  useHistoryStore(
    useShallow((s) => selector(s.primitives.getCurrentConversation())),
  );
export const useMessage = (messageId: string | undefined | null) =>
  useHistoryStore((s) =>
    messageId
      ? s.primitives.getCurrentConversation().history[messageId]
      : undefined,
  );
export const useMessageIds = () =>
  useHistoryStore(
    useShallow((s) =>
      Object.keys(s.primitives.getCurrentConversation().history),
    ),
  );
export const useMessages = () =>
  useHistoryStore(
    useShallow((s) =>
      Object.values(s.primitives.getCurrentConversation().history),
    ),
  );
