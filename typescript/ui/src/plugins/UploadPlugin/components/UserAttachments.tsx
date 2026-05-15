import { useState } from "react";
import { Icon } from "@iconify/react";
import { SlotPropsMap } from "../../../core/types/slots";

interface AttachmentPreview {
  filename: string;
  mimeType?: string;
  blobUrl?: string;
}

function isAttachmentPreview(value: unknown): value is AttachmentPreview {
  return (
    typeof value === "object" &&
    value !== null &&
    "filename" in value &&
    typeof (value as { filename: unknown }).filename === "string"
  );
}

function AttachmentThumbnail({
  att,
  idx,
}: {
  att: AttachmentPreview;
  idx: number;
}) {
  const [hasError, setHasError] = useState(false);
  const showIcon = !att.blobUrl || hasError;

  return (
    <div
      className="border-default-200 bg-default-100 rounded-medium flex items-center gap-2 border p-1"
      data-testid={`user-attachment-${idx}`}
    >
      {showIcon ? (
        <div className="bg-default-200 flex h-10 w-10 items-center justify-center rounded">
          <Icon icon="heroicons:photo" className="text-default-500 h-5 w-5" />
        </div>
      ) : (
        <img
          src={att.blobUrl}
          alt={att.filename}
          className="h-16 w-16 rounded object-cover"
          onError={() => setHasError(true)}
        />
      )}
      <span className="text-default-700 max-w-[10rem] truncate text-xs">
        {att.filename}
      </span>
    </div>
  );
}

export default function UserAttachments({
  message,
}: SlotPropsMap["message.userBubble.prepend"]) {
  const raw = message.extra?.attachments;
  if (!Array.isArray(raw)) return null;
  const items = raw.filter(isAttachmentPreview);
  if (items.length === 0) return null;

  return (
    <div className="mb-2 flex flex-wrap gap-2" data-testid="user-attachments">
      {items.map((att, idx) => (
        <AttachmentThumbnail
          key={`${att.filename}-${idx}`}
          att={att}
          idx={idx}
        />
      ))}
    </div>
  );
}
