import { useUploadAttachmentsStore } from "../stores/attachmentsStore";
import { SlotPropsMap } from "../../../core/types/slots";
import AttachmentChip from "./AttachmentChip";

export default function AttachmentPreviewSlot({
  isInputDisabled,
}: SlotPropsMap["prompt.attachments"]) {
  const pending = useUploadAttachmentsStore((s) => s.pending);
  const remove = useUploadAttachmentsStore((s) => s.remove);

  if (pending.length === 0) return null;

  return (
    <div
      className="flex flex-wrap items-center gap-2 px-2 pt-2"
      data-testid="attachment-preview-slot"
    >
      {pending.map((att) => (
        <AttachmentChip
          key={att.id}
          attachment={att}
          onRemove={remove}
          isDisabled={isInputDisabled}
        />
      ))}
    </div>
  );
}
