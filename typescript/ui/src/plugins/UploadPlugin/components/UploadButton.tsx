import { Button } from "@heroui/react";
import { Icon } from "@iconify/react";
import { ChangeEvent, useRef } from "react";
import { useRagbitsCall } from "@ragbits/api-client-react";
import { SlotPropsMap } from "../../../core/types/slots";

export default function UploadButton({
  isInputDisabled,
}: SlotPropsMap["prompt.beforeSend"]) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { call: uploadFile, isLoading: isUploading } =
    useRagbitsCall("/api/upload");
  const handleFileClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const formData = new FormData();
      formData.append("file", file);
      await uploadFile({
        method: "POST",
        body: formData,
      });
    } catch (err) {
      console.error("Upload failed", err);
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };
  return (
    <>
      <input
        type="file"
        ref={fileInputRef}
        className="hidden"
        onChange={handleFileChange}
      />
      <Button
        isIconOnly
        aria-label="Upload file"
        variant="ghost"
        onPress={handleFileClick}
        isLoading={isUploading}
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
