import { JWTToken, User } from "@ragbits/api-client-react";
import { createStore } from "zustand";
import { immer } from "zustand/middleware/immer";

export interface AuthStore {
  user: User | null;
  token: JWTToken | null;
  tokenExpiration: number | null;
  isAuthenticated: boolean;

  login: (user: User, token: JWTToken) => void;
  logout: () => void;
}

export const authStore = createStore(
  immer<AuthStore>((set) => ({
    user: null,
    token: null,
    isAuthenticated: false,
    tokenExpiration: null,

    login: (user, token) =>
      set(() => ({
        user,
        token,
        tokenExpiration: Date.now() + token.expires_in * 1000,
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
