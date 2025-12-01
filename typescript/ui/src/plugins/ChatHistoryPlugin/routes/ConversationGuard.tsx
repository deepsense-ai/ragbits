import { PropsWithChildren, useEffect } from "react";
import { useHistoryStore } from "../../../core/stores/HistoryStore/useHistoryStore";
import { useNavigate, useParams } from "react-router";
import { useShallow } from "zustand/shallow";
import { useHistoryActions } from "../../../core/stores/HistoryStore/selectors";
import { getConversationRoute } from "../utils";

export default function ConversationGuard({ children }: PropsWithChildren) {
  const navigate = useNavigate();
  const conversations = useHistoryStore(
    useShallow((s) => Object.keys(s.conversations)),
  );
  const { selectConversation } = useHistoryActions();
  const params = useParams();
  const conversationId = params.conversationId;
  const isValidConversation =
    conversationId &&
    typeof conversationId === "string" &&
    conversations.includes(conversationId);

  useEffect(() => {
    if (isValidConversation) {
      selectConversation(conversationId);
      return;
    }

    const newestConversation = conversations.at(-1);
    if (!newestConversation) {
      throw new Error("No conversation to navigate to");
    }
    selectConversation(newestConversation);
    navigate(getConversationRoute(newestConversation), { replace: true });
  }, [
    conversations,
    isValidConversation,
    navigate,
    selectConversation,
    conversationId,
  ]);

  return children;
}
