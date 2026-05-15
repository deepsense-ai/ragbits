import { AttachmentsConfig } from "@ragbits/api-client";

export type ValidationError =
  | { kind: "config-missing" }
  | { kind: "too-many"; limit: number }
  | { kind: "too-large"; limitBytes: number }
  | { kind: "wrong-type"; allowed: string[] };

export function validateFile(
  file: File,
  config: AttachmentsConfig | null,
  currentCount: number,
): ValidationError | null {
  if (!config) {
    return { kind: "config-missing" };
  }
  if (currentCount >= config.max_attachments_per_message) {
    return { kind: "too-many", limit: config.max_attachments_per_message };
  }
  const limitBytes = config.max_size_mb * 1024 * 1024;
  if (file.size > limitBytes) {
    return { kind: "too-large", limitBytes };
  }
  if (!config.allowed_mime_types.includes(file.type)) {
    return { kind: "wrong-type", allowed: config.allowed_mime_types };
  }
  return null;
}

export function formatValidationError(error: ValidationError): string {
  switch (error.kind) {
    case "config-missing":
      return "Uploads are currently unavailable.";
    case "too-many":
      return `Too many attachments — limit is ${error.limit} per message.`;
    case "too-large": {
      const limitMb = Math.round(error.limitBytes / (1024 * 1024));
      return `File too large — limit is ${limitMb} MB.`;
    }
    case "wrong-type":
      return `File type not supported. Allowed: ${error.allowed.join(", ")}.`;
  }
}
