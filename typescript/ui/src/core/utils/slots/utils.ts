import { LazyExoticComponent, FunctionComponent, ComponentType } from "react";
import { PluginSlot, SlotName, SlotPropsMap } from "../../types/slots";

export function makeSlot<S extends SlotName>(
  slot: S,
  component:
    | LazyExoticComponent<FunctionComponent<SlotPropsMap[S]>>
    | ComponentType<SlotPropsMap[S]>,
  priority?: number,
  condition?: () => boolean,
): PluginSlot<S> {
  return { slot, component, priority, condition };
}
