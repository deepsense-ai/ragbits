import { JWTToken, User } from "@ragbits/api-client-react";
import { createStore } from "zustand";
import { persist } from "zustand/middleware";
import { immer } from "zustand/middleware/immer";

export interface AuthStore {
  user: User | null;
  token: JWTToken | null;
  tokenExpiration: number | null;
  isAuthenticated: boolean;
  hasHydrated: boolean;

  login: (user: User, token: JWTToken) => void;
  logout: () => void;
  onRehydrated: () => void;
}

const pickUserForStorage = (u: User): Partial<User> => ({
  user_id: u.user_id,
  email: u.email,
});

export const authStore = createStore(
  persist(
    immer<AuthStore>((set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      tokenExpiration: null,
      hasHydrated: false,

      onRehydrated: () => {
        const { token, tokenExpiration, logout } = get();
        const now = Date.now();
        const timeUntilExpiration = (tokenExpiration ?? 0) - now;

        if (!token || timeUntilExpiration <= 0) {
          logout();
        } else {
          set((draft) => {
            draft.isAuthenticated = true;
          });
        }

        set((draft) => {
          draft.hasHydrated = true;
        });
      },
      login: (user, token) =>
        set((draft) => {
          draft.user = user;
          draft.token = token;
          draft.tokenExpiration = Date.now() + 30 * 1000;
          draft.isAuthenticated = true;
        }),

      logout: () =>
        set((draft) => {
          draft.user = null;
          draft.token = null;
          draft.isAuthenticated = false;
        }),
    })),
    {
      name: "ragbits-auth",
      partialize: (s: AuthStore) => ({
        token: s.token,
        tokenExpiration: s.tokenExpiration,
        user: s.user ? pickUserForStorage(s.user) : null,
      }),
      merge: (persistedState, currentState) => {
        return {
          ...currentState,
          ...(persistedState as Record<string, unknown>),
          isAuthenticated: false,
        };
      },
      onRehydrateStorage: (state) => {
        return () => {
          state.onRehydrated();
        };
      },
    },
  ),
);
