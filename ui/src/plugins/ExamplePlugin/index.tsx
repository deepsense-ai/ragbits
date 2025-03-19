import { lazy } from "react";
import { Plugin } from "../../core/utils/plugins/PluginManager";

export const ExamplePluginName = "ExamplePlugin";

type ExamplePluginComponents = "ExampleComponent";
export const ExamplePlugin: Plugin<ExamplePluginComponents> = {
  name: ExamplePluginName,
  components: {
    ExampleComponent: lazy(() => import("./ExamplePluginComponent")),
  },
  onActivate: () => {
    console.log("ExamplePlugin activated");
  },
  onDeactivate: () => {
    console.log("ExamplePlugin deactivated");
  },
};
