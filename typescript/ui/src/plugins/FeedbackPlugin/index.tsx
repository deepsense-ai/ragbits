import { lazy } from "react";
import { createPlugin } from "../../core/utils/plugins/utils";

const FeedbackForm = lazy(() => import("./components/FeedbackForm"));

export const FeedbackFormPluginName = "FeedbackFormPlugin";
export const FeedbackFormPlugin = createPlugin({
  name: FeedbackFormPluginName,
  components: {
    FeedbackForm,
  },
  slots: [
    {
      slot: "message.actions",
      component: FeedbackForm,
      priority: 5,
    },
  ],
});
