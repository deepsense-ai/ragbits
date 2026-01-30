import { lazy } from "react";
import { createPlugin } from "../../core/utils/plugins/utils";
import ConversationRoute from "./routes/ConversationRoute";
import ConversationGuard from "./routes/ConversationGuard";
import { makeSlot } from "../../core/utils/slots/utils";

const ChatHistory = lazy(() => import("./components/ChatHistory"));

export const ChatHistoryPluginName = "ChatHistoryPlugin";
export const ChatHistoryPlugin = createPlugin({
  name: ChatHistoryPluginName,
  components: {
    ChatHistory,
  },
  routes: [
    {
      target: `/`,
      path: `/conversation/:conversationId`,
      element: <ConversationRoute />,
    },
  ],
  routeWrappers: [
    {
      target: "/",
      wrapper: (children) => <ConversationGuard>{children}</ConversationGuard>,
    },
  ],
  slots: [makeSlot("layout.sidebar", ChatHistory, 10)],
});
