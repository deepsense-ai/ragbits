import { lazy } from "react";
import { createPlugin } from "../../core/utils/plugins/utils";

export const UsagePluginName = "UsagePluginName";
export const UsagePlugin = createPlugin({
  name: UsagePluginName,
  components: {
    UsageButton: lazy(() => import("./components/UsageButton")),
  },
});
