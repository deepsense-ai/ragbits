import { useState, useCallback, useRef } from "react";
import type {
  ApiRequestOptions,
  StreamCallbacks,
  ChatResponse,
} from "ragbits-api-client";
import type { RagbitsCallResult, RagbitsStreamResult } from "./types";
import { useRagbitsContext } from "./RagbitsProvider";

/**
 * Generic hook for making API calls to Ragbits endpoints
 * @param endpoint - The API endpoint (e.g., "/api/config", "/api/feedback")
 * @param defaultOptions - Default options for the API call
 */
export function useRagbitsCall<T = any>(
  endpoint: string,
  defaultOptions?: ApiRequestOptions
): RagbitsCallResult<T> {
  const { client } = useRagbitsContext();
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const call = useCallback(
    async (options: ApiRequestOptions = {}): Promise<T> => {
      setIsLoading(true);
      setError(null);

      try {
        const mergedOptions = { ...defaultOptions, ...options };
        // Use the generic overload of makeRequest to avoid type constraints
        const result = await (client as any).makeRequest(
          endpoint,
          mergedOptions
        );
        setData(result);
        return result;
      } catch (err) {
        const error = err instanceof Error ? err : new Error("API call failed");
        setError(error);
        throw error;
      } finally {
        setIsLoading(false);
      }
    },
    [client, endpoint, defaultOptions]
  );

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setIsLoading(false);
  }, []);

  return {
    data,
    error,
    isLoading,
    call,
    reset,
  };
}

/**
 * Hook for handling streaming responses from Ragbits endpoints
 */
export function useRagbitsStream<T = ChatResponse>(): RagbitsStreamResult<T> {
  const { client } = useRagbitsContext();
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const cancelRef = useRef<(() => void) | null>(null);

  const cancel = useCallback(() => {
    if (cancelRef.current) {
      cancelRef.current();
      cancelRef.current = null;
      setIsStreaming(false);
    }
  }, []);

  const stream = useCallback(
    (
      endpoint: string,
      data: any,
      callbacks: StreamCallbacks<T>
    ): (() => void) => {
      // Cancel any existing stream
      cancel();

      setError(null);
      setIsStreaming(true);

      const cancelFn = (
        client as {
          makeStreamRequest<T>(
            endpoint: string,
            data: any,
            callbacks: StreamCallbacks<T>
          ): () => void;
        }
      ).makeStreamRequest<T>(endpoint, data, {
        onMessage: callbacks.onMessage,
        onError: (err: string) => {
          const error = new Error(err);
          setError(error);
          setIsStreaming(false);
          callbacks.onError(err);
        },
        onClose: () => {
          setIsStreaming(false);
          callbacks.onClose?.();
        },
      });

      cancelRef.current = cancelFn;
      return cancelFn;
    },
    [client, cancel]
  );

  return {
    isStreaming,
    error,
    stream,
    cancel,
  };
}
