import { useParams } from "react-router";
import App from "../../../App";
import { useHistoryActions } from "../../../core/stores/HistoryStore/selectors";
import { useHistoryStore } from "../../../core/stores/HistoryStore/useHistoryStore";
import { useEffect } from "react";

export default function HistoryRoute() {
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

  return <App />;
}
