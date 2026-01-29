import {
  Context,
  FunctionComponent,
  LazyExoticComponent,
  useContext,
  useSyncExternalStore,
} from "react";
import { Plugin } from "../../types/plugins";
import { identity, noop } from "lodash";
import { StoreApi } from "zustand";

export function createPlugin<
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  T extends Record<string, LazyExoticComponent<FunctionComponent<any>>>,
>(plugin: Plugin<T>): Plugin<T> {
  return plugin;
}

/**
 * This is experimental implementation of dynamic plugin stores.
 * The idea is that plugin components use "static" version of the store,
 * while other components can use the store in "reactive" manner by utilizing this
 * hook. In case of plugin being disabled, the hook simply returns `[undefined, false]`.
 */
export function useDynamicStore<TStore extends Record<string, unknown>>(
  storeContext: Context<StoreApi<TStore> | null>,
) {
  const store = useContext(storeContext);
  const slice = useSyncExternalStore(
    store ? store.subscribe : () => noop,
    () => (store ? identity(store.getState()) : null),
    () => (store ? identity(store.getInitialState()) : null),
  );
  return <T>(selector: (s: TStore) => T): [T | undefined, boolean] => {
    if (!store) {
      return [undefined, false];
    }

    return [selector(slice as TStore), true];
  };
}
