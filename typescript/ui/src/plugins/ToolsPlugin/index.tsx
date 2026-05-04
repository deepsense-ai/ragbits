import { lazy } from "react";
import { createPlugin } from "../../core/utils/plugins/utils";
import { makeSlot } from "../../core/utils/slots/utils";

const ToolsPanel = lazy(() => import("./components/ToolsPanel"));

export const ToolsPluginName = "ToolsPlugin";
export const ToolsPlugin = createPlugin({
  name: ToolsPluginName,
  components: {
    ToolsPanel,
  },
  slots: [makeSlot("layout.sidebarBottom", ToolsPanel, 5)],
});
