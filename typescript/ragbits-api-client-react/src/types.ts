import type {
  ApiRequestOptions,
  StreamCallbacks,
  RagbitsClient,
} from "ragbits-api-client";

// Re-export core types from ragbits-api-client
export type {
  ChatResponse,
  ChatRequest,
  FeedbackRequest,
  StreamCallbacks,
  ClientConfig,
  ApiRequestOptions,
  RagbitsClient,
  Message,
  Reference,
} from "ragbits-api-client";

// Re-export enums as values
export { MessageRole, ChatResponseType } from "ragbits-api-client";

// React-specific hook result types
export interface RagbitsCallResult<T> {
  data: T | null;
  error: Error | null;
  isLoading: boolean;
  call: (options?: ApiRequestOptions) => Promise<T>;
  reset: () => void;
}

export interface RagbitsStreamResult<T> {
  isStreaming: boolean;
  error: Error | null;
  stream: (
    endpoint: string,
    data: any,
    callbacks: StreamCallbacks<T>
  ) => () => void;
  cancel: () => void;
}

// Provider context type
export interface RagbitsContextValue {
  client: RagbitsClient;
}
