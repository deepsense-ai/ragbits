import { lazy } from "react";
import { createPlugin } from "../../core/utils/plugins/utils";
import { makeSlot } from "../../core/utils/slots/utils";

const UploadButton = lazy(() => import("./components/UploadButton"));

export const UploadPluginName = "UploadPlugin";
export const UploadPlugin = createPlugin({
  name: UploadPluginName,
  components: {
    UploadButton,
  },
  slots: [makeSlot("prompt.beforeSend", UploadButton, 5)],
});
