import { useSyncExternalStore } from "react";
import { SlotName } from "../../types/slots";
import { pluginManager } from "../plugins/PluginManager";

export function useSlotHasFillers(slot: SlotName): boolean {
  return useSyncExternalStore(
    (cb) => pluginManager.subscribe(cb),
    () => pluginManager.hasSlotFillers(slot),
  );
}
