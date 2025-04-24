import { MessageRole, Reference } from "./api";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  references?: Reference[];
}
