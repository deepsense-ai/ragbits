import { createStore } from "zustand";
import { immer } from "zustand/middleware/immer";

export interface User {
  email: string;
}

export interface AuthStore {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;

  login: (user: User, token: string) => void;
  logout: () => void;
}

export const authStore = createStore(
  immer<AuthStore>((set) => ({
    user: null,
    token: null,
    isAuthenticated: false,

    login: (user, token) =>
      set(() => ({
        user,
        token,
        isAuthenticated: true,
      })),

    logout: () =>
      set(() => ({
        user: null,
        token: null,
        isAuthenticated: false,
      })),
  })),
);
