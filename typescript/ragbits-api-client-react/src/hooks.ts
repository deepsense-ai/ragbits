import { useState, useCallback, useRef } from "react";
import type {
  ApiRequestOptions,
  StreamCallbacks,
  ChatResponse,
  ApiEndpointPath,
  ApiEndpointResponse,
  StreamingEndpointPath,
  StreamingEndpointStream,
} from "ragbits-api-client";
import type { RagbitsCallResult, RagbitsStreamResult } from "./types";
import { useRagbitsContext } from "./RagbitsProvider";

/**
 * Hook for making API calls to Ragbits endpoints
 * - Only predefined routes are allowed
 * - Response type can be overridden with explicit type parameter
 * @param endpoint - The predefined API endpoint
 * @param defaultOptions - Default options for the API call
 */
export function useRagbitsCall<
  TEndpoint extends ApiEndpointPath,
  TResponse = ApiEndpointResponse<TEndpoint>
>(
  endpoint: TEndpoint,
  defaultOptions?: ApiRequestOptions
): RagbitsCallResult<TResponse> {
  const { client } = useRagbitsContext();
  const [data, setData] = useState<TResponse | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  const abort = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsLoading(false);
    }
  }, []);

  const call = useCallback(
    async (options: ApiRequestOptions = {}): Promise<TResponse> => {
      // Abort any existing request
      abort();

      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      setIsLoading(true);
      setError(null);

      try {
        const mergedOptions = {
          ...defaultOptions,
          ...options,
          headers: {
            ...defaultOptions?.headers,
            ...options.headers,
          },
        };

        // Add abort signal to the request options
        const requestOptions = {
          ...mergedOptions,
          signal: abortController.signal,
        };

        // Use the generic overload of makeRequest to avoid type constraints
        const result = await (client as any).makeRequest(
          endpoint,
          requestOptions
        );

        // Only update state if request wasn't aborted
        if (!abortController.signal.aborted) {
          setData(result);
          abortControllerRef.current = null;
        }

        return result;
      } catch (err) {
        // Only update error state if request wasn't aborted
        if (!abortController.signal.aborted) {
          const error =
            err instanceof Error ? err : new Error("API call failed");
          setError(error);
          abortControllerRef.current = null;
          throw error;
        }
        throw err;
      } finally {
        // Only update loading state if request wasn't aborted
        if (!abortController.signal.aborted) {
          setIsLoading(false);
        }
      }
    },
    [client, endpoint, defaultOptions, abort]
  );

  const reset = useCallback(() => {
    abort();
    setData(null);
    setError(null);
    setIsLoading(false);
  }, [abort]);

  return {
    data,
    error,
    isLoading,
    call,
    reset,
    abort,
  };
}

/**
 * Hook for handling streaming responses from Ragbits endpoints
 * - Only predefined streaming routes are allowed
 * - Response type can be overridden with explicit type parameter
 * @param endpoint - The predefined streaming endpoint
 */
export function useRagbitsStream<
  TEndpoint extends StreamingEndpointPath,
  TResponse = StreamingEndpointStream<TEndpoint>
>(endpoint: TEndpoint): RagbitsStreamResult<TResponse> {
  const { client } = useRagbitsContext();
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const cancel = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsStreaming(false);
    }
  }, []);

  const stream = useCallback(
    (
      data: any,
      callbacks: StreamCallbacks<TResponse, string>
    ): (() => void) => {
      // Cancel any existing stream
      cancel();

      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      setError(null);
      setIsStreaming(true);

      const cancelFn = (
        client as {
          makeStreamRequest<T>(
            endpoint: string,
            data: any,
            callbacks: StreamCallbacks<T, Error>,
            signal?: AbortSignal
          ): () => void;
        }
      ).makeStreamRequest<TResponse>(
        endpoint,
        data,
        {
          onMessage: callbacks.onMessage,
          onError: (err: Error) => {
            // Only update state if not aborted
            if (!abortController.signal.aborted) {
              setError(err);
              setIsStreaming(false);
              callbacks.onError(err.message); // Convert Error to string for user callback
            }
          },
          onClose: () => {
            // Only update state if not aborted
            if (!abortController.signal.aborted) {
              setIsStreaming(false);
              callbacks.onClose?.();
            }
          },
        },
        abortController.signal
      );

      return () => {
        cancel();
        cancelFn();
      };
    },
    [client, cancel, endpoint]
  );

  return {
    isStreaming,
    error,
    stream,
    cancel,
  };
}
