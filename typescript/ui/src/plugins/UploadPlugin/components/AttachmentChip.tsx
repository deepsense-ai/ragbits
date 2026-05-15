import { useState } from "react";
import { Button } from "@heroui/react";
import { Icon } from "@iconify/react";
import { PendingAttachment } from "../stores/attachmentsStore";

interface AttachmentChipProps {
  attachment: PendingAttachment;
  onRemove: (id: string) => void;
  isDisabled?: boolean;
}

export default function AttachmentChip({
  attachment,
  onRemove,
  isDisabled,
}: AttachmentChipProps) {
  const isFailed = attachment.status === "failed";
  const isLoading = attachment.status === "uploading";
  const errorMessage = attachment.status === "failed" ? attachment.error : null;
  const [imageErrored, setImageErrored] = useState(false);

  return (
    <div
      data-testid={`attachment-chip-${attachment.id}`}
      data-status={attachment.status}
      className={
        "border-default-200 bg-default-100 rounded-medium relative flex items-center gap-2 border py-1 pr-7 pl-1 " +
        (isFailed ? "border-danger-300 bg-danger-50" : "")
      }
    >
      {imageErrored ? (
        <div className="bg-default-200 flex h-10 w-10 items-center justify-center rounded">
          <Icon
            icon="heroicons:document"
            className="text-default-500 h-5 w-5"
          />
        </div>
      ) : (
        <img
          src={attachment.blobUrl}
          alt={attachment.filename}
          className={
            "h-10 w-10 rounded object-cover " + (isLoading ? "opacity-60" : "")
          }
          onError={() => setImageErrored(true)}
        />
      )}
      <div className="flex min-w-0 flex-col">
        <span className="text-default-700 max-w-[10rem] truncate text-xs">
          {attachment.filename}
        </span>
        {errorMessage && (
          <span className="text-danger flex items-center gap-1 text-xs">
            <Icon icon="heroicons:x-circle" className="h-3.5 w-3.5" />
            {errorMessage}
          </span>
        )}
      </div>
      {isLoading && (
        <Icon
          icon="heroicons:arrow-path"
          className="text-default-500 h-4 w-4 animate-spin"
          aria-label="Uploading"
        />
      )}
      <Button
        isIconOnly
        size="sm"
        variant="light"
        radius="full"
        aria-label={`Remove ${attachment.filename}`}
        onPress={() => onRemove(attachment.id)}
        isDisabled={isDisabled}
        className="absolute top-0 right-0 h-5 w-5 min-w-0"
        data-testid={`attachment-chip-remove-${attachment.id}`}
      >
        <Icon icon="heroicons:x-mark" width={14} />
      </Button>
    </div>
  );
}
