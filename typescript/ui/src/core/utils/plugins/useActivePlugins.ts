import { useSyncExternalStore } from "react";
import { pluginManager } from "./PluginManager";

export function useActivePlugins() {
  const subscribe = (callback: () => void) => {
    return pluginManager.subscribe(callback);
  };

  const getSnapshot = () => {
    return pluginManager.getActivePlugins();
  };

  return useSyncExternalStore(subscribe, getSnapshot);
}
