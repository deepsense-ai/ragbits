import { lazy } from "react";
import { Plugin } from "../../core/utils/plugins/PluginManager";

export const FeedbackFormPluginName = "FeedbackFormPlugin";

type FeedbackFormPluginComponents = "FeedbackFormComponent";

export const FeedbackFormPlugin: Plugin<FeedbackFormPluginComponents> = {
  name: FeedbackFormPluginName,
  components: {
    FeedbackFormComponent: lazy(() => import("./FeedbackFormPluginComponent")),
  },
};
