import {
  ComponentType,
  FunctionComponent,
  LazyExoticComponent,
  ReactNode,
} from "react";
import { SlotName, SlotPropsMap } from "./slots";

// Slot registration within a plugin
export interface PluginSlot<S extends SlotName = SlotName> {
  slot: S;
  component:
    | LazyExoticComponent<FunctionComponent<SlotPropsMap[S]>>
    | ComponentType<SlotPropsMap[S]>;
  priority?: number; // Higher = rendered first
  condition?: () => boolean; // Dynamic visibility
}

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
  slots?: PluginSlot[];
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
