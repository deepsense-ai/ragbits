import { PropsWithChildren, useEffect, useState } from "react";
import { useHistoryStore } from "../../../core/stores/HistoryStore/useHistoryStore";
import { useNavigate, useParams } from "react-router";
import { useShallow } from "zustand/shallow";
import { useHistoryActions } from "../../../core/stores/HistoryStore/selectors";
import { getConversationRoute } from "../utils";
import { useRagbitsContext } from "@ragbits/api-client-react";
import { isTemporaryConversation } from "../../../core/stores/HistoryStore/utils";

export default function ConversationGuard({ children }: PropsWithChildren) {
  const navigate = useNavigate();
  const { client: ragbitsClient } = useRagbitsContext();
  const conversations = useHistoryStore(
    useShallow((s) => Object.keys(s.conversations)),
  );
  const { selectConversation, loadSharedConversation, newConversation } =
    useHistoryActions();
  const params = useParams();
  const conversationId = params.conversationId;
  const isKnown =
    conversationId &&
    typeof conversationId === "string" &&
    conversations.includes(conversationId);
  const isTemp =
    typeof conversationId === "string" &&
    isTemporaryConversation(conversationId);
  const isServerOnly = useHistoryStore(
    (s) =>
      conversationId != null &&
      s.conversations[conversationId]?.isServerOnly === true,
  );
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fallbackToHomeConversation = () => {
      const newestConversation = conversations.at(-1);
      const target = newestConversation ?? newConversation();
      selectConversation(target);
      navigate(getConversationRoute(target), { replace: true });
    };

    // Temp IDs are local-only placeholders for unsent conversations; the
    // backend has no record of them, so don't waste a round-trip just to 404.
    const needsFetch = !isTemp && (!isKnown || isServerOnly);

    if (conversationId && needsFetch && !loading) {
      setLoading(true);
      loadSharedConversation(conversationId, ragbitsClient).then((loaded) => {
        setLoading(false);
        if (loaded) {
          selectConversation(conversationId);
        } else if (isKnown) {
          selectConversation(conversationId);
        } else {
          fallbackToHomeConversation();
        }
      });
      return;
    }

    if (isKnown && !isServerOnly) {
      selectConversation(conversationId);
      return;
    }

    // Either no conversationId in the route, or a temp/local id that the
    // store no longer knows about (e.g. after a logout/login wipe). Either
    // way, fall back to the most recent conversation we have, or spin up a
    // brand-new one if the store is empty.
    if (!conversationId || (isTemp && !isKnown)) {
      fallbackToHomeConversation();
    }
  }, [
    conversations,
    isKnown,
    isTemp,
    isServerOnly,
    navigate,
    selectConversation,
    loadSharedConversation,
    newConversation,
    conversationId,
    loading,
    ragbitsClient,
  ]);

  return children;
}
