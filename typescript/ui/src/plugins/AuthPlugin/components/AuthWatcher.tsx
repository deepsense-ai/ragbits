import { useEffect } from "react";
import { useStore } from "zustand";
import { authStore } from "../stores/authStore";
import { useRagbitsCall } from "@ragbits/api-client-react";
import { useInitializeUserStore } from "../../../core/stores/HistoryStore/useInitializeUserStore";
import { useLocation, useNavigate } from "react-router";

/**
 * Ensures that we logout users when the session expires
 */
export function AuthWatcher() {
  const { logout, login, setHydrated } = useStore(authStore, (s) => s);
  const initializeUserStore = useInitializeUserStore();
  const navigate = useNavigate();
  const userRequestFactory = useRagbitsCall("/api/user");
  const location = useLocation(); // For redirecting to home page if user is logged in and on login page
  // Check session on mount
  useEffect(() => {
    const checkSession = async () => {
      try {
        const user = await userRequestFactory.call();
        if (user) {
          login(user);
          // Initialize the history store with user-specific key
          initializeUserStore(user.user_id);
          if (location.pathname === "/login") {
            navigate("/");
          }
        } else {
          logout();
        }
      } catch (error) {
        console.error("Failed to check session:", error);
        logout();
        navigate("/login");
      } finally {
        setHydrated();
      }
    };

    checkSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Run only once on mount

  return null;
}
