import { lazy } from "react";
import { createPlugin } from "../../core/utils/plugins/utils";
import { makeSlot } from "../../core/utils/slots/utils";

const UsageButton = lazy(() => import("./components/UsageButton"));

export const UsagePluginName = "UsagePluginName";
export const UsagePlugin = createPlugin({
  name: UsagePluginName,
  components: {
    UsageButton,
  },
  slots: [makeSlot("message.actions", UsageButton, 10)],
});
