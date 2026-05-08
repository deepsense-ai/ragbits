import { Icon } from "@iconify/react";
import { useConversationProperty } from "../../../core/stores/HistoryStore/selectors";

export default function SharedBanner() {
  const isShared = useConversationProperty((s) => s.isShared);
  const sharedBy = useConversationProperty((s) => s.sharedBy);

  if (!isShared || !sharedBy) return null;

  return (
    <div className="bg-default-100 text-default-600 mb-4 flex items-center gap-2 rounded-lg px-4 py-2 text-sm">
      <Icon icon="heroicons:link" width={16} />
      <span>Shared by {sharedBy}</span>
    </div>
  );
}
