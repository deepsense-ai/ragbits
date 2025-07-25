import { lazy } from "react";
import { createPlugin } from "../../core/utils/plugins/utils";

export const ChatHistoryPluginName = "ChatHistoryPlugin";
export const ChatHistoryPlugin = createPlugin({
  name: ChatHistoryPluginName,
  components: {
    ChatHistory: lazy(() => import("./components/ChatHistory")),
  },
});
