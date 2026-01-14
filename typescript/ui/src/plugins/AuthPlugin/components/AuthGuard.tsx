import { PropsWithChildren } from "react";
import { Navigate, useLocation } from "react-router";
import { authStore } from "../stores/authStore";
import { useStore } from "zustand";
import { AuthStoreContextProvider } from "../contexts/AuthStoreContext/AuthStoreContextProvider";
import InitializationScreen from "../../../core/components/InitializationScreen";
import { RagbitsContextProvider } from "@ragbits/api-client-react";
import { API_URL } from "../../../config";
import { AuthWatcher } from "./AuthWatcher";

export default function AuthGuard({ children }: PropsWithChildren) {
  const location = useLocation();
  const isAuthenticated = useStore(authStore, (s) => s.isAuthenticated);
  const hasHydrated = useStore(authStore, (s) => s.hasHydrated);
  const onUnauthorized = useStore(authStore, (s) => s.logout);

  if (!hasHydrated) {
    // Wrap the AuthWatcher and InitializationScreen with RagbitsContextProvider to enable cookie credentials
    return (
      <RagbitsContextProvider
        baseUrl={API_URL}
        auth={{ credentials: "include" }}
      >
        <AuthWatcher />
        <InitializationScreen />
      </RagbitsContextProvider>
    );
  }

  if (location.pathname === "/login") {
    // Wrap login page with RagbitsContextProvider to enable cookie credentials
    return (
      <RagbitsContextProvider
        baseUrl={API_URL}
        auth={{
          credentials: "include",
        }}
      >
        {children}
      </RagbitsContextProvider>
    );
  }

  return isAuthenticated ? (
    <AuthStoreContextProvider>
      {/*
        Shadow the unauthorized RagbitsContextProvider with the authorized one.
        For session-based auth, cookies are automatically included in requests
        via credentials: "include", so no token is needed here.
      */}
      <RagbitsContextProvider
        baseUrl={API_URL}
        auth={{
          onUnauthorized,
          credentials: "include",
        }}
      >
        {children}
      </RagbitsContextProvider>
    </AuthStoreContextProvider>
  ) : (
    <Navigate to="/login" replace />
  );
}
