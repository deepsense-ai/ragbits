import { createStore, useStore } from "zustand";
import { immer } from "zustand/middleware/immer";

export interface AttachmentsStore {
  pending: File[];

  add: (file: File) => void;
  remove: (index: number) => void;
  clear: () => void;
}

export const attachmentsStore = createStore(
  immer<AttachmentsStore>((set) => ({
    pending: [],

    add: (file) =>
      set((draft) => {
        draft.pending.push(file);
      }),

    remove: (index) =>
      set((draft) => {
        draft.pending.splice(index, 1);
      }),

    clear: () =>
      set((draft) => {
        draft.pending = [];
      }),
  })),
);

export const useAttachmentsStore = <T>(
  selector: (state: AttachmentsStore) => T,
): T => useStore(attachmentsStore, selector);
