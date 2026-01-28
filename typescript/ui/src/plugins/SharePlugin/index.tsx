import { lazy } from "react";
import { createPlugin } from "../../core/utils/plugins/utils";

const ShareButton = lazy(() => import("./components/ShareButton"));

export const SharePluginName = "SharePluginName";
export const SharePlugin = createPlugin({
  name: SharePluginName,
  components: {
    ShareButton,
  },
  slots: [
    {
      slot: "layout.headerActions",
      component: ShareButton,
      priority: 5,
    },
  ],
});
