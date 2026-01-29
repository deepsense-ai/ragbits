import { lazy } from "react";
import { createPlugin } from "../../core/utils/plugins/utils";
import { makeSlot } from "../../core/utils/slots/utils";

const FeedbackForm = lazy(() => import("./components/FeedbackForm"));

export const FeedbackFormPluginName = "FeedbackFormPlugin";
export const FeedbackFormPlugin = createPlugin({
  name: FeedbackFormPluginName,
  components: {
    FeedbackForm,
  },
  slots: [makeSlot("message.actions", FeedbackForm, 5)],
});
