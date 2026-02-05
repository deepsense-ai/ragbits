import { FunctionComponent, LazyExoticComponent, ReactNode } from "react";
import { AnyPluginSlot, PluginSlot, SlotName } from "./slots";

// Re-export for convenience
export type { AnyPluginSlot, PluginSlot, SlotName };

export interface Plugin<
  T extends Record<
    string,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    LazyExoticComponent<FunctionComponent<any>>
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
  > = Record<string, LazyExoticComponent<FunctionComponent<any>>>,
> {
  name: string;
  onActivate?: () => void;
  onDeactivate?: () => void;
  components: T;
  routes?: PluginRoute[];
  routeWrappers?: PluginRouteWrapper[];
  slots?: AnyPluginSlot[];
  metadata?: Record<string, unknown>;
}

export interface PluginRoute {
  path: string;
  element: ReactNode;
  children?: PluginRoute[];
  target?: `/${string}`;
}

export type PluginRouteWrapper = {
  target?: `/${string}` | "global";
  wrapper: (element: ReactNode) => ReactNode;
};
