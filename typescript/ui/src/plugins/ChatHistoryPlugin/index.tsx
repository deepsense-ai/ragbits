import { lazy } from "react";
import { createPlugin } from "../../core/utils/plugins/utils";
import ConversationRoute from "./routes/ConversationRoute";
import ConversationGuard from "./routes/ConversationGuard";

export const ChatHistoryPluginName = "ChatHistoryPlugin";
export const ChatHistoryPlugin = createPlugin({
  name: ChatHistoryPluginName,
  components: {
    ChatHistory: lazy(() => import("./components/ChatHistory")),
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
});
