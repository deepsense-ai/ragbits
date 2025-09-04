import { useCallback, useEffect, useRef } from "react";
import { useNavigate } from "react-router";
import { useStore } from "zustand";
import { authStore } from "../stores/authStore";
import { useConversationProperty } from "../../../core/stores/HistoryStore/selectors";

/**
 * Ensures that we logout users when the token exipres
 */
export function AuthWatcher() {
  const { token, tokenExpiration, logout } = useStore(authStore, (s) => s);
  const isConversationLoading = useConversationProperty((s) => s.isLoading);
  const navigate = useNavigate();
  const loadingRef = useRef(isConversationLoading);

  useEffect(() => {
    loadingRef.current = isConversationLoading;
  }, [isConversationLoading]);

  const handleLogoutWhenReady = useCallback(() => {
    const check = () => {
      if (!loadingRef.current) {
        logout();
        navigate("/login");
      } else {
        setTimeout(check, 500);
      }
    };
    check();
  }, [logout, navigate]);

  useEffect(() => {
    if (!token || !tokenExpiration) return;

    const now = Date.now();
    const timeUntilExpiration = tokenExpiration - now;

    if (timeUntilExpiration <= 0) {
      handleLogoutWhenReady();
      return;
    }

    const timeoutId = setTimeout(() => {
      handleLogoutWhenReady();
    }, timeUntilExpiration);

    return () => clearTimeout(timeoutId);
  }, [token, tokenExpiration, handleLogoutWhenReady]);

  return null;
}
