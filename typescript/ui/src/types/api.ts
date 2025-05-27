// Import shared types and enums from ragbits packages
import { ChatResponseType } from "ragbits-api-client-react";

import type { Reference } from "ragbits-api-client-react";

// Re-export for external use
export { MessageRole, ChatResponseType } from "ragbits-api-client-react";

export type {
  Message,
  Reference,
  ChatRequest,
  FeedbackRequest,
} from "ragbits-api-client-react";

// Remove the duplicated Method type and use ApiRequestOptions instead
export type Method = "GET" | "POST";
export interface RequestConfig<T = undefined> {
  method: Method;
  body?: T;
}

// App-specific enums and interfaces that should remain
export enum FormEnabler {
  LIKE = "like_enabled",
  DISLIKE = "dislike_enabled",
}

export enum FormType {
  LIKE = "like_form",
  DISLIKE = "dislike_form",
}

export enum FormFieldType {
  TEXT = "text",
  SELECT = "select",
}

export interface FormFieldResponse {
  name: string;
  label: string;
  type: FormFieldType;
  required: boolean;
  options?: string[];
}

export interface FormSchemaResponse {
  title: string;
  fields: FormFieldResponse[];
}

export type ConfigResponse<
  TFormType extends string | number | symbol = FormType,
  TFormEnabler extends string | number | symbol = FormEnabler,
> = {} & {
  [key in TFormType]: FormSchemaResponse | null;
} & {
  [key in TFormEnabler]: boolean;
};

// App-specific server state interface
export interface ServerState {
  state: Record<string, unknown>;
  signature: string;
}

// App-specific chat response types that extend the base ones
interface MessageIdChatResponse {
  type: ChatResponseType.MESSAGE_ID;
  content: string;
}

interface TextChatResponse {
  type: ChatResponseType.TEXT;
  content: string;
}

interface ReferenceChatResponse {
  type: ChatResponseType.REFERENCE;
  content: Reference;
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
