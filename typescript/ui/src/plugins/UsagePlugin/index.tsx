import { lazy } from "react";
import { createPlugin } from "../../core/utils/plugins/utils";

const UsageButton = lazy(() => import("./components/UsageButton"));

export const UsagePluginName = "UsagePluginName";
export const UsagePlugin = createPlugin({
  name: UsagePluginName,
  components: {
    UsageButton,
  },
  slots: [
    {
      slot: "message.actions",
      component: UsageButton,
      priority: 10, // Higher = rendered first
    },
  ],
});
