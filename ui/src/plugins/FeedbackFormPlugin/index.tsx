import { lazy } from "react";
import { createPlugin } from "../../core/utils/plugins/utils";

export const FeedbackFormPluginName = "FeedbackFormPlugin";
export const FeedbackFormPlugin = createPlugin({
  name: FeedbackFormPluginName,
  components: {
    FeedbackFormComponent: lazy(() => import("./FeedbackFormPluginComponent")),
    ExampleComponent: lazy(
      () => import("../ExamplePlugin/ExamplePluginComponent"),
    ),
  },
});
