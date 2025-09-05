import { PropsWithChildren } from "react";
import { Navigate, useLocation } from "react-router";
import { authStore } from "../stores/authStore";
import { useStore } from "zustand";
import { AuthStoreContextProvider } from "../contexts/AuthStoreContext/AuthStoreContextProvider";
import { AuthWatcher } from "./AuthWatcher";
import InitializationScreen from "../../../core/components/InitializationScreen";
import { RagbitsContextProvider } from "@ragbits/api-client-react";
import { API_URL } from "../../../config";

export default function AuthGuard({ children }: PropsWithChildren) {
  const location = useLocation();
  const isAuthenticated = useStore(authStore, (s) => s.isAuthenticated);
  const hasHydrated = useStore(authStore, (s) => s.hasHydrated);

  const token = useStore(authStore, (s) => s.token?.access_token);
  const onUnauthorized = useStore(authStore, (s) => s.logout);

  if (!hasHydrated) {
    return <InitializationScreen />;
  }

  if (location.pathname === "/login") {
    return children;
  }

  return isAuthenticated && !!token ? (
    <AuthStoreContextProvider>
      {/*
        Shadow the unauthorized RagbitsContextProvider with the authorized one.
        Note: If the complexity or number of options increases, consider introducing a
        global <ClientSettingsProvider> above the original <RagbitsContextProvider> and
        use it to store and provide configuration to that provider.
        If you choose that solution, remove this provider.
      */}
      <RagbitsContextProvider
        baseUrl={API_URL}
        auth={{
          getToken: () => token,
          onUnauthorized,
        }}
      >
        {children}
        <AuthWatcher />
      </RagbitsContextProvider>
    </AuthStoreContextProvider>
  ) : (
    <Navigate to="/login" replace />
  );
}
