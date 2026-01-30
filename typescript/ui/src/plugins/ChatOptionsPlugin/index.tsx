import { lazy } from "react";
import { createPlugin } from "../../core/utils/plugins/utils";
import { makeSlot } from "../../core/utils/slots/utils";

const ChatOptionsForm = lazy(() => import("./components/ChatOptionsForm"));

export const ChatOptionsPluginName = "ChatOptionsPlugin";
export const ChatOptionsPlugin = createPlugin({
  name: ChatOptionsPluginName,
  components: {
    ChatOptionsForm,
  },
  slots: [makeSlot("prompt.beforeSend", ChatOptionsForm, 10)],
});
