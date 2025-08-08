import { PropsWithChildren } from "react";
import { Navigate, useLocation } from "react-router";
import { authStore } from "../stores/authStore";
import { useStore } from "zustand";
import { AuthStoreContextProvider } from "../contexts/AuthStoreContext/AuthStoreContextProvider";
import { AuthWatcher } from "./AuthWatcher";

export default function AuthGuard({ children }: PropsWithChildren) {
  const location = useLocation();
  const isAuthenticated = useStore(authStore, (s) => s.isAuthenticated);

  if (location.pathname === "/login") {
    return children;
  }

  return isAuthenticated ? (
    <AuthStoreContextProvider>
      {children}
      <AuthWatcher />
    </AuthStoreContextProvider>
  ) : (
    <Navigate to="/login" replace />
  );
}
