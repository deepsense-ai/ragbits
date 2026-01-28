import { lazy } from "react";
import { createPlugin } from "../../core/utils/plugins/utils";

const ChatOptionsForm = lazy(() => import("./components/ChatOptionsForm"));

export const ChatOptionsPluginName = "ChatOptionsPlugin";
export const ChatOptionsPlugin = createPlugin({
  name: ChatOptionsPluginName,
  components: {
    ChatOptionsForm,
  },
  slots: [
    {
      slot: "prompt.beforeSend",
      component: ChatOptionsForm,
      priority: 10,
    },
  ],
});
