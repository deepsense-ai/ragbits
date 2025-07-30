import { createContext } from "react";
import { createStore } from "zustand";
import { AuthStore } from "../../stores/authStore";

export const AuthStoreContext = createContext<ReturnType<
  typeof createStore<AuthStore, [["zustand/immer", never]]>
> | null>(null);
