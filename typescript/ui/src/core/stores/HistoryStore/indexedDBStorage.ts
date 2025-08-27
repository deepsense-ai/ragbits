import { get, set, del } from "idb-keyval";
import { debounce } from "lodash";
import { StateStorage } from "zustand/middleware";

export const IndexedDBStorage: StateStorage = {
  getItem: async (name: string): Promise<string | null> => {
    return (await get(name)) || null;
  },
  // Debounce is used as a counter measure for race conditions when reviving the store from storage
  setItem: debounce(async (name: string, value: string): Promise<void> => {
    await set(name, value);
  }, 500),
  removeItem: async (name: string): Promise<void> => {
    await del(name);
  },
};
