export type Method = "GET" | "POST";
export interface RequestConfig<T = undefined> {
  method: Method;
  body?: T;
}

export enum MessageRole {
  USER = "user",
  ASSISTANT = "assistant",
  SYSTEM = "system",
}

export interface Message {
  role: MessageRole;
  content: string;
}

export interface Reference {
  title: string;
  content: string;
  url?: string;
}

export enum ChatResponseType {
  TEXT = "text",
  REFERENCE = "reference",
  MESSAGE_ID = "message_id",
  STATE_UPDATE = "state_update",
}

export interface ChatRequest {
  message: string;
  history: Message[];
  context?: object;
}

interface TextChatResponse {
  type: ChatResponseType.TEXT;
  content: string;
}

interface ReferenceChatResponse {
  type: ChatResponseType.REFERENCE;
  content: Reference;
}

interface MessageIdChatResponse {
  type: ChatResponseType.MESSAGE_ID;
  content: string;
}

export interface ServerState {
  state: Record<string, unknown>;
  signature: string;
}

interface StateUpdateChatResponse {
  type: ChatResponseType.STATE_UPDATE;
  content: ServerState;
}

export type ChatResponse =
  | TextChatResponse
  | ReferenceChatResponse
  | MessageIdChatResponse
  | StateUpdateChatResponse;

export enum FormType {
  LIKE = "like_form",
  DISLIKE = "dislike_form",
}

export enum FormFieldType {
  TEXT = "text",
  SELECT = "select",
}

interface FormFieldResponse {
  name: string;
  label: string;
  type: FormFieldType;
  required: boolean;
  options?: { label: string; value: string }[];
}

export interface FormSchemaResponse {
  title: string;
  fields: FormFieldResponse[];
}

export interface ConfigResponse {
  [FormType.LIKE]?: FormSchemaResponse | null;
  [FormType.DISLIKE]?: FormSchemaResponse | null;
}
