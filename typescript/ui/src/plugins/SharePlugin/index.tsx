import { lazy } from "react";
import { createPlugin } from "../../core/utils/plugins/utils";
import { makeSlot } from "../../core/utils/slots/utils";

const ShareButton = lazy(() => import("./components/ShareButton"));

export const SharePluginName = "SharePluginName";
export const SharePlugin = createPlugin({
  name: SharePluginName,
  components: {
    ShareButton,
  },
  slots: [makeSlot("layout.headerActions", ShareButton, 5)],
});
