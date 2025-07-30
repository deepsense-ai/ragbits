import { useParams } from "react-router";
import { useHistoryActions } from "../../../core/stores/HistoryStore/selectors";
import { useHistoryStore } from "../../../core/stores/HistoryStore/useHistoryStore";
import { useEffect } from "react";
import Chat from "../../../core/components/Chat";

export default function ConversationRoute() {
  const params = useParams();
  const currentConversation = useHistoryStore((s) => s.currentConversation);
  const conversationId = params.conversationId;
  const { selectConversation } = useHistoryActions();
  if (!conversationId || typeof conversationId !== "string") {
    throw new Error(
      "HistoryRoute expects `conversationId` param to be present in the URL.",
    );
  }

  useEffect(() => {
    if (currentConversation === conversationId) {
      return;
    }

    selectConversation(conversationId);
  }, [conversationId, currentConversation, selectConversation]);

  return <Chat />;
}
