import { FunctionComponent, LazyExoticComponent, ReactNode } from "react";

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
