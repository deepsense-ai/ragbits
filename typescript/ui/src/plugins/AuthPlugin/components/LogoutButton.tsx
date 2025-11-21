import { Button } from "@heroui/react";
import { useStore } from "zustand";
import { authStore } from "../stores/authStore";
import { Icon } from "@iconify/react/dist/iconify.js";
import DelayedTooltip from "../../../core/components/DelayedTooltip";
import { useRagbitsCall } from "@ragbits/api-client-react";
import { useNavigate } from "react-router";

export default function LogoutButton() {
  const logoutRequestFactory = useRagbitsCall("/api/auth/logout", {
    headers: {
      "Content-Type": "application/json",
    },
    method: "POST",
  });
  const logout = useStore(authStore, (s) => s.logout);
  const isAuthenticated = useStore(authStore, (s) => s.isAuthenticated);
  const navigate = useNavigate();

  const handleLogout = async () => {
    if (!isAuthenticated) {
      navigate("/login");
      return;
    }

    try {
      // No body needed - session is in HTTP-only cookie
      const response = await logoutRequestFactory.call();

      if (!response.success) {
        return;
      }

      logout();
      navigate("/login");
    } catch (e) {
      console.error("Failed to logout", e);
    }
  };

  return (
    <DelayedTooltip content="Logout" placement="bottom">
      <Button
        isIconOnly
        aria-label="Logout"
        variant="ghost"
        onPress={handleLogout}
        data-testid="logout-button"
      >
        <Icon icon="heroicons:arrow-left-start-on-rectangle" />
      </Button>
    </DelayedTooltip>
  );
}
