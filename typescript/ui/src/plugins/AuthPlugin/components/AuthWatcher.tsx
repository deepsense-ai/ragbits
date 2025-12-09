import { useEffect } from "react";
import { useStore } from "zustand";
import { authStore } from "../stores/authStore";
import { useRagbitsContext } from "@ragbits/api-client-react";
import { useInitializeUserStore } from "../../../core/stores/HistoryStore/useInitializeUserStore";

/**
 * Ensures that we logout users when the session expires
 */
export function AuthWatcher() {
  const { logout, login, setHydrated } = useStore(authStore, (s) => s);
  const { client } = useRagbitsContext();
  const initializeUserStore = useInitializeUserStore();

  // Check session on mount
  useEffect(() => {
    const checkSession = async () => {
      try {
        const user = await client.makeRequest("/api/user");
        if (user) {
          login(user);
          // Initialize the history store with user-specific key
          initializeUserStore(user.user_id);
        } else {
          logout();
        }
      } catch (error) {
        console.error("Failed to check session:", error);
        logout();
      } finally {
        setHydrated();
        navigate("/login");
      }
    };

    checkSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Run only once on mount

  return null;
}
