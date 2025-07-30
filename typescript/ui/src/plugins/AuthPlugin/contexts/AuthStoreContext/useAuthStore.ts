import { identity, noop } from "lodash";
import { useContext, useSyncExternalStore } from "react";
import { AuthStore } from "../../stores/authStore";
import { AuthStoreContext } from "./AuthStoreContext";

/**
 * This is experimental implementation of dynamic plugin stores.
 * The idea is that plugin components use "static" version of the store,
 * while other components can use the store in "reactive" manner by utilizing this
 * hook. In case of plugin being disabled, the hook simply returns `[undefined, false]`.
 *
 * TODO: Abstract this mechanism into plugin manager
 */
export const useAuthStore = () => {
  const store = useContext(AuthStoreContext);
  const slice = useSyncExternalStore(
    store ? store.subscribe : () => noop,
    () => (store ? identity(store.getState()) : null),
    () => (store ? identity(store.getInitialState()) : null),
  );
  return <T>(selector: (s: AuthStore) => T): [T | undefined, boolean] => {
    if (!store) return [undefined, false];
    return [selector(slice as AuthStore), true];
  };
};
