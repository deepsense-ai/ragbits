import { Button } from "@heroui/react";
import { useStore } from "zustand";
import { authStore } from "../stores/authStore";
import { Icon } from "@iconify/react/dist/iconify.js";
import DelayedTooltip from "../../../core/components/DelayedTooltip";

export default function LogoutButton() {
  const logut = useStore(authStore, (s) => s.logout);
  return (
    <DelayedTooltip content="Logout" placement="bottom">
      <Button
        isIconOnly
        aria-label="Logout"
        variant="ghost"
        onPress={logut}
        data-testid="logout-button"
      >
        <Icon icon="heroicons:arrow-left-start-on-rectangle" />
      </Button>
    </DelayedTooltip>
  );
}
