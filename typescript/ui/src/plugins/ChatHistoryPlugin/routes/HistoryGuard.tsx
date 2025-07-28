import { PropsWithChildren } from "react";
import { useHistoryStore } from "../../../core/stores/HistoryStore/useHistoryStore";
import { Navigate, useParams } from "react-router";
import { useShallow } from "zustand/shallow";
import { useHistoryActions } from "../../../core/stores/HistoryStore/selectors";

export default function HistoryGuard({ children }: PropsWithChildren) {
  const conversations = useHistoryStore(
    useShallow((s) => Object.keys(s.conversations)),
  );
  const { selectConversation } = useHistoryActions();
  const params = useParams();
  const conversationId = params.conversationId;
  const isValidURL =
    conversationId &&
    typeof conversationId === "string" &&
    conversations.includes(conversationId);

  if (!isValidURL) {
    const newestConversation = conversations.at(-1);
    if (!newestConversation) {
      throw new Error("No conversation to navigate to");
    }
    selectConversation(newestConversation);
    return <Navigate to={`/history/${newestConversation}`} replace />;
  }

  return children;
}
