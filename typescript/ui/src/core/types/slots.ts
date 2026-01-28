import { ChatMessage } from "./history";

export type SlotName =
  | "layout.sidebar"
  | "layout.headerActions"
  | "message.actions"
  | "prompt.beforeSend";

export interface SlotPropsMap {
  "layout.sidebar": never;
  "layout.headerActions": never;
  "message.actions": {
    message: ChatMessage;
    content: string;
    serverId?: string;
  };
  "prompt.beforeSend": never;
}
