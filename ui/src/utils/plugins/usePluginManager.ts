import { useSyncExternalStore } from "react";
import { pluginManager } from "./PluginManager";

export const usePluginManager = (pluginName: string) => {
  const subscribe = (callback: () => void) => {
    return pluginManager.subscribe(callback);
  };

  const getSnapshot = () => {
    return pluginManager.getPlugin(pluginName);
  };

  return useSyncExternalStore(subscribe, getSnapshot);
};
