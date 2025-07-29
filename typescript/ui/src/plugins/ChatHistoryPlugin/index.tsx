import { lazy } from "react";
import { createPlugin } from "../../core/utils/plugins/utils";
import HistoryRoute from "./routes/HistoryRoute";
import HistoryGuard from "./routes/HistoryGuard";

export const ChatHistoryPluginName = "ChatHistoryPlugin";
export const ChatHistoryPlugin = createPlugin({
  name: ChatHistoryPluginName,
  components: {
    ChatHistory: lazy(() => import("./components/ChatHistory")),
  },
  routes: [
    {
      target: `/`,
      path: `/history/:conversationId`,
      element: <HistoryRoute />,
    },
  ],
  routeWrappers: [
    {
      target: "global",
      wrapper: (children) => <HistoryGuard>{children}</HistoryGuard>,
    },
  ],
});
