import { User } from "@ragbits/api-client-react";
import { createStore } from "zustand";
import { immer } from "zustand/middleware/immer";

export interface AuthStore {
  user: User | null;
  isAuthenticated: boolean;
  hasHydrated: boolean;

  login: (user: User) => void;
  logout: () => void;
  setHydrated: () => void;
}

export const authStore = createStore(
  immer<AuthStore>((set) => ({
    user: null,
    isAuthenticated: false,
    hasHydrated: false,

    login: (user) =>
      set((draft) => {
        draft.user = user;
        draft.isAuthenticated = true;
      }),

    logout: () =>
      set((draft) => {
        draft.user = null;
        draft.isAuthenticated = false;
      }),

    setHydrated: () =>
      set((draft) => {
        draft.hasHydrated = true;
      }),
  })),
);
