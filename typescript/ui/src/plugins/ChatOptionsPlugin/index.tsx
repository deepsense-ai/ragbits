import { lazy } from "react";
import { createPlugin } from "../../core/utils/plugins/utils";

export const ChatOptionsPluginName = "ChatOptionsPlugin";
export const ChatOptionsPlugin = createPlugin({
  name: ChatOptionsPluginName,
  components: {
    ChatOptionsForm: lazy(() => import("./components/ChatOptionsForm")),
  },
});
