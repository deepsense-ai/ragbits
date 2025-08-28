import { useParams } from "react-router";
import Chat from "../../../core/components/Chat";

export default function ConversationRoute() {
  const params = useParams();
  const conversationId = params.conversationId;
  if (!conversationId || typeof conversationId !== "string") {
    throw new Error(
      "HistoryRoute expects `conversationId` param to be present in the URL.",
    );
  }

  return <Chat />;
}
