import { lazy } from "react";
import { createPlugin } from "../../core/utils/plugins/utils";

export const SharePluginName = "SharePluginName";
export const SharePlugin = createPlugin({
  name: SharePluginName,
  components: {
    ShareButton: lazy(() => import("./components/ShareButton")),
  },
});
