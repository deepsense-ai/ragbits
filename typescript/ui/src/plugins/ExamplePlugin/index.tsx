import { lazy } from "react";
import { createPlugin } from "../../core/utils/plugins/utils";

export const ExamplePluginName = "ExamplePlugin";
export const ExamplePlugin = createPlugin({
  name: ExamplePluginName,
  components: {
    ExampleComponent: lazy(() => import("./components/ExamplePluginComponent")),
  },
  onActivate: () => {
    console.log("ExamplePlugin activated");
  },
  onDeactivate: () => {
    console.log("ExamplePlugin deactivated");
  },
  slots: [],
});
