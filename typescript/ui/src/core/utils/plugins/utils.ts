import { FunctionComponent, LazyExoticComponent } from "react";
import { Plugin } from "../../../types/plugins";

export function createPlugin<
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  T extends Record<string, LazyExoticComponent<FunctionComponent<any>>>,
>(plugin: Plugin<T>): Plugin<T> {
  return plugin;
}
