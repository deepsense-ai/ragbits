import { lazy } from "react";
import { createPlugin } from "../../core/utils/plugins/utils";
import { makeSlot } from "../../core/utils/slots/utils";

const ShareButton = lazy(() => import("./components/ShareButton"));
const SharedBanner = lazy(() => import("./components/SharedBanner"));
const SharedItemIcon = lazy(() => import("./components/SharedItemIcon"));

export const SharePluginName = "SharePluginName";
export const SharePlugin = createPlugin({
  name: SharePluginName,
  components: {
    ShareButton,
    SharedBanner,
    SharedItemIcon,
  },
  slots: [
    makeSlot("layout.headerActions", ShareButton, 5),
    makeSlot("chat.banner.top", SharedBanner, 10),
    makeSlot("chatHistory.itemDecorator", SharedItemIcon, 10),
  ],
});
