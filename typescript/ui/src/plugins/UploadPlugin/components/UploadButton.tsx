import { Button } from "@heroui/react";
import { Icon } from "@iconify/react";
import { ChangeEvent, useEffect, useRef } from "react";
import { SlotPropsMap } from "../../../core/types/slots";
import { useConfigContext } from "../../../core/contexts/ConfigContext/useConfigContext";
import { useUploadAttachmentsStore } from "../stores/attachmentsStore";
import { processFile } from "../upload";

export default function UploadButton({
  isInputDisabled,
}: SlotPropsMap["prompt.beforeSend"]) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const {
    config: { attachments: attachmentsConfig },
  } = useConfigContext();

  useEffect(() => {
    useUploadAttachmentsStore.getState().setConfig(attachmentsConfig);
  }, [attachmentsConfig]);

  const handleFileClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    for (const file of Array.from(files)) processFile(file);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  return (
    <>
      <input
        type="file"
        ref={fileInputRef}
        className="hidden"
        multiple
        onChange={handleFileChange}
      />
      <Button
        isIconOnly
        aria-label="Attach files"
        variant="ghost"
        onPress={handleFileClick}
        isDisabled={isInputDisabled}
        className="p-0"
        data-testid="upload-file-button"
      >
        <Icon
          className="text-default-500"
          icon="heroicons:paper-clip"
          width={20}
        />
      </Button>
    </>
  );
}
