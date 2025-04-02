import { MessageRole, Reference } from "./api";

export interface ChatMessage {
  role: MessageRole;
  content: string;
  references?: Reference[];
}
