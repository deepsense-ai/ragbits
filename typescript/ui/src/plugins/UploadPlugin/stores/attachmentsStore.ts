import { create } from "zustand";

interface BaseAttachment {
  id: string;
  filename: string;
  mimeType: string;
  blobUrl: string;
}

interface UploadingAttachment extends BaseAttachment {
  status: "uploading";
}

interface ReadyAttachment extends BaseAttachment {
  status: "ready";
  file: File;
}

interface FailedAttachment extends BaseAttachment {
  status: "failed";
  error: string;
  retryFile?: File;
}

export type PendingAttachment =
  | UploadingAttachment
  | ReadyAttachment
  | FailedAttachment;

export const activeCount = (pending: PendingAttachment[]): number =>
  pending.filter((a) => a.status !== "failed").length;

export interface AttachmentPreview {
  filename: string;
  mimeType: string;
  blobUrl: string;
}

interface UploadAttachmentsStore {
  pending: PendingAttachment[];
  add: (file: File) => string;
  addFailed: (file: File, error: string, retryFile?: File) => void;
  markReady: (id: string, file: File) => void;
  markFailed: (id: string, error: string) => void;
  remove: (id: string) => void;
  clear: () => void;
  consumeReady: () => {
    files: File[];
    previews: AttachmentPreview[];
  };
}

const revokeBlob = (att: PendingAttachment): void => {
  URL.revokeObjectURL(att.blobUrl);
};

export const useUploadAttachmentsStore = create<UploadAttachmentsStore>(
  (set, get) => ({
    pending: [],
    add: (file: File) => {
      const id = crypto.randomUUID();
      const entry: UploadingAttachment = {
        id,
        filename: file.name,
        mimeType: file.type || "application/octet-stream",
        blobUrl: URL.createObjectURL(file),
        status: "uploading",
      };
      set((state) => ({ pending: [...state.pending, entry] }));
      return id;
    },
    addFailed: (file: File, error: string, retryFile?: File) => {
      const entry: FailedAttachment = {
        id: crypto.randomUUID(),
        filename: file.name,
        mimeType: file.type || "application/octet-stream",
        blobUrl: URL.createObjectURL(file),
        status: "failed",
        error,
        retryFile,
      };
      set((state) => ({ pending: [...state.pending, entry] }));
    },
    markReady: (id, file) =>
      set((state) => ({
        pending: state.pending.map((a) =>
          a.id === id ? { ...a, status: "ready", file } : a,
        ),
      })),
    markFailed: (id, error) =>
      set((state) => ({
        pending: state.pending.map((a) =>
          a.id === id ? { ...a, status: "failed", error } : a,
        ),
      })),
    remove: (id) => {
      const att = get().pending.find((a) => a.id === id);
      if (att) revokeBlob(att);
      set((state) => ({ pending: state.pending.filter((a) => a.id !== id) }));
    },
    clear: () => {
      get().pending.forEach(revokeBlob);
      set({ pending: [] });
    },
    consumeReady: () => {
      const state = get();
      const ready = state.pending.filter(
        (a): a is ReadyAttachment => a.status === "ready",
      );
      // Ready chips travel with the message (their blob URLs stay alive for
      // in-session thumbnails). Failed/in-flight chips are dropped, blobs revoked.
      state.pending.forEach((a) => {
        if (a.status !== "ready") revokeBlob(a);
      });
      set({ pending: [] });
      return {
        files: ready.map((a) => a.file),
        previews: ready.map((a) => ({
          filename: a.filename,
          mimeType: a.mimeType,
          blobUrl: a.blobUrl,
        })),
      };
    },
  }),
);
