import {
  activeCount,
  useUploadAttachmentsStore,
} from "./stores/attachmentsStore";
import { formatValidationError, validateFile } from "./validation";

export function processFile(file: File): void {
  const store = useUploadAttachmentsStore.getState();
  const error = validateFile(file, store.config, activeCount(store.pending));
  if (error) {
    store.addFailed(file, formatValidationError(error));
    return;
  }
  const id = store.add(file);
  store.markReady(id, file);
}
