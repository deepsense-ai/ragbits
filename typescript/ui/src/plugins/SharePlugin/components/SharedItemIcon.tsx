import { Icon } from "@iconify/react";
import { useHistoryStore } from "../../../core/stores/HistoryStore/useHistoryStore";

interface SharedItemIconProps {
  conversationId: string;
}

export default function SharedItemIcon({
  conversationId,
}: SharedItemIconProps) {
  const isShared = useHistoryStore(
    (s) => s.conversations[conversationId]?.isShared ?? false,
  );

  if (!isShared) return null;

  return (
    <Icon
      icon="heroicons:link"
      className="text-default-400 shrink-0"
      width={14}
    />
  );
}
