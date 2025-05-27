/**
 * Message roles for chat conversations
 */
export enum MessageRole {
  USER = "user",
  ASSISTANT = "assistant",
  SYSTEM = "system",
}

/**
 * Message structure for chat conversations
 */
export interface Message {
  role: MessageRole;
  content: string;
  id?: string;
}

/**
 * Reference structure for document references
 */
export interface Reference {
  title: string;
  content: string;
  url?: string;
}

/**
 * Response types from the API
 */
export enum ChatResponseType {
  MESSAGE = "message",
  REFERENCE = "reference",
  STATE_UPDATE = "state_update",
  TEXT = "text",
  MESSAGE_ID = "message_id",
}

/**
 * Chat response from the API
 */
export interface ChatResponse {
  type: ChatResponseType;
  content: any;
}

/**
 * Base chat request to the API
 */
export interface BaseChatRequest {
  message: string;
  history: Message[];
  context?: Record<string, unknown>;
}

/**
 * Chat request to the API with optional extensions
 */
export type ChatRequest<T extends Record<string, unknown> = {}> =
  BaseChatRequest & T;

/**
 * Feedback request to the API
 */
export interface FeedbackRequest {
  message_id: string;
  feedback: string;
  payload: Record<string, unknown> | null;
}

/**
 * Configuration for the client
 */
export interface ClientConfig {
  baseUrl?: string;
}

/**
 * Callbacks for handling streaming responses
 */
export interface StreamCallbacks<T> {
  onMessage: (data: T) => void | Promise<void>;
  onError: (error: string) => void | Promise<void>;
  onClose?: () => void | Promise<void>;
}

/**
 * Regular API endpoint definitions with their request/response types
 */
export interface ApiEndpoints {
  "/api/config": {
    method: "GET";
    request: never;
    response: Record<string, unknown>;
  };
  "/api/feedback": {
    method: "POST";
    request: FeedbackRequest;
    response: Record<string, unknown>;
  };
}

/**
 * Streaming API endpoint definitions with their request/stream response types
 */
export interface StreamingEndpoints {
  "/api/chat": {
    method: "POST";
    request: ChatRequest;
    stream: ChatResponse;
  };
}

/**
 * Extract endpoint paths as a union type
 */
export type ApiEndpointPath = keyof ApiEndpoints;

/**
 * Extract streaming endpoint paths as a union type
 */
export type StreamingEndpointPath = keyof StreamingEndpoints;

/**
 * Extract request type for a specific API endpoint
 */
export type ApiEndpointRequest<T extends ApiEndpointPath> =
  ApiEndpoints[T]["request"];

/**
 * Extract response type for a specific API endpoint
 */
export type ApiEndpointResponse<T extends ApiEndpointPath> =
  ApiEndpoints[T]["response"];

/**
 * Extract HTTP method for a specific API endpoint
 */
export type ApiEndpointMethod<T extends ApiEndpointPath> =
  ApiEndpoints[T]["method"];

/**
 * Extract request type for a specific streaming endpoint
 */
export type StreamingEndpointRequest<T extends StreamingEndpointPath> =
  StreamingEndpoints[T]["request"];

/**
 * Extract stream response type for a specific streaming endpoint
 */
export type StreamingEndpointStream<T extends StreamingEndpointPath> =
  StreamingEndpoints[T]["stream"];

/**
 * Extract HTTP method for a specific streaming endpoint
 */
export type StreamingEndpointMethod<T extends StreamingEndpointPath> =
  StreamingEndpoints[T]["method"];

/**
 * Typed request options for specific API endpoints
 */
export interface TypedApiRequestOptions<T extends ApiEndpointPath> {
  method?: ApiEndpointMethod<T>;
  body?: ApiEndpointRequest<T> extends never
    ? undefined
    : ApiEndpointRequest<T>;
  headers?: Record<string, string>;
}

/**
 * Generic request options for API calls
 */
export interface ApiRequestOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE" | "PATCH";
  body?: any;
  headers?: Record<string, string>;
}
