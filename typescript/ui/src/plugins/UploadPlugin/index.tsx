import { lazy } from "react";
import { createPlugin } from "../../core/utils/plugins/utils";
import { makeSlot } from "../../core/utils/slots/utils";
import { registerFileDropHandler } from "../../core/utils/fileHandlers";
import { registerPreSendContributor } from "../../core/utils/messageContext";
import { useUploadAttachmentsStore } from "./stores/attachmentsStore";
import { processFile } from "./upload";

const UploadButton = lazy(() => import("./components/UploadButton"));
const AttachmentPreviewSlot = lazy(
  () => import("./components/AttachmentPreviewSlot"),
);
const UserAttachments = lazy(() => import("./components/UserAttachments"));

let unregisterContributor: (() => void) | null = null;
let unregisterDropHandler: (() => void) | null = null;

export const UploadPluginName = "UploadPlugin";
export const UploadPlugin = createPlugin({
  name: UploadPluginName,
  components: {
    UploadButton,
    AttachmentPreviewSlot,
    UserAttachments,
  },
  slots: [
    makeSlot("prompt.beforeSend", UploadButton, 5),
    makeSlot("prompt.attachments", AttachmentPreviewSlot, 5),
    makeSlot("message.userBubble.prepend", UserAttachments, 5),
  ],
  onActivate: () => {
    unregisterContributor = registerPreSendContributor(() => {
      const { files, previews } = useUploadAttachmentsStore
        .getState()
        .consumeReady();
      if (files.length === 0) return null;
      return {
        files,
        userMessageExtra: { attachments: previews },
      };
    });
    unregisterDropHandler = registerFileDropHandler((files) => {
      files.forEach(processFile);
    });
  },
  onDeactivate: () => {
    unregisterContributor?.();
    unregisterContributor = null;
    unregisterDropHandler?.();
    unregisterDropHandler = null;
    useUploadAttachmentsStore.getState().clear();
  },
});
