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
  ClientConfig,
  ApiRequestOptions,
  RagbitsClient,
  Message,
  Reference,
} from "ragbits-api-client";

// Re-export enums as values
export { MessageRole, ChatResponseType } from "ragbits-api-client";

// React-specific hook result types
export interface RagbitsCallResult<T, E = Error> {
  data: T | null;
  error: E | null;
  isLoading: boolean;
  call: (options?: ApiRequestOptions) => Promise<T>;
  reset: () => void;
  abort: () => void;
}

export interface RagbitsStreamResult<T, E = Error> {
  isStreaming: boolean;
  error: E | null;
  stream: (
    endpoint: string,
    data: any,
    callbacks: StreamCallbacks<T, string>
  ) => () => void;
  cancel: () => void;
}

// Provider context type
export interface RagbitsContextValue {
  client: RagbitsClient;
}
