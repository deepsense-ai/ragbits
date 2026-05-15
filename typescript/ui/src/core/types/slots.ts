import { ComponentType, FunctionComponent, LazyExoticComponent } from "react";
import { ChatMessage } from "./history";

export type SlotName =
  | "layout.sidebar"
  | "layout.headerActions"
  | "message.actions"
  | "message.userBubble.prepend"
  | "prompt.attachments"
  | "prompt.beforeSend";

export interface SlotPropsMap {
  "layout.sidebar": Record<string, never>;
  "layout.headerActions": Record<string, never>;
  "message.actions": {
    message: ChatMessage;
    content: string;
    serverId?: string;
  };
  "message.userBubble.prepend": {
    message: ChatMessage;
  };
  "prompt.attachments": {
    isInputDisabled: boolean;
  };
  "prompt.beforeSend": {
    isInputDisabled: boolean;
  };
}

// Type-safe slot definition for plugin authors
export interface PluginSlot<S extends SlotName> {
  slot: S;
  component:
    | LazyExoticComponent<FunctionComponent<SlotPropsMap[S]>>
    | ComponentType<SlotPropsMap[S]>;
  priority?: number;
  condition?: () => boolean;
}

export type AnyPluginSlot = {
  [S in SlotName]: PluginSlot<S>;
}[SlotName];

// Internal type for slot storage/rendering
export interface StoredSlot {
  slot: SlotName;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  component: LazyExoticComponent<FunctionComponent<any>> | ComponentType<any>;
  priority?: number;
  condition?: () => boolean;
}
