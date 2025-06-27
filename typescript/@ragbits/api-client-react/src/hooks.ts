import { useState, useCallback, useRef } from 'react'
import type {
    StreamCallbacks,
    ApiEndpointPath,
    ApiEndpointResponse,
    TypedApiRequestOptions,
    StreamingEndpointPath,
    StreamingEndpointStream,
    StreamingEndpointRequest,
} from '@ragbits/api-client'
import type { RagbitsCallResult, RagbitsStreamResult } from './types'
import { useRagbitsContext } from './RagbitsProvider'

/**
 * Hook for making API calls to Ragbits endpoints
 * - Only predefined routes are allowed
 * - Response type can be overridden with explicit type parameter
 * @param endpoint - The predefined API endpoint
 * @param defaultOptions - Default options for the API call
 */
export function useRagbitsCall<
    TEndpoint extends ApiEndpointPath,
    TResponse = ApiEndpointResponse<TEndpoint>,
>(
    endpoint: TEndpoint,
    defaultOptions?: TypedApiRequestOptions<TEndpoint>
): RagbitsCallResult<TResponse, Error, TEndpoint> {
    const { client } = useRagbitsContext()
    const [data, setData] = useState<TResponse | null>(null)
    const [error, setError] = useState<Error | null>(null)
    const [isLoading, setIsLoading] = useState(false)
    const abortControllerRef = useRef<AbortController | null>(null)

    const abort = useCallback(() => {
        if (!abortControllerRef.current) {
            return null
        }

        abortControllerRef.current.abort()
        abortControllerRef.current = null
        setIsLoading(false)
    }, [])

    const call = useCallback(
        async (
            options: TypedApiRequestOptions<TEndpoint> = {}
        ): Promise<TResponse> => {
            // Abort any existing request only if there's one in progress
            if (abortControllerRef.current && isLoading) {
                abortControllerRef.current.abort()
            }

            const abortController = new AbortController()
            abortControllerRef.current = abortController

            setIsLoading(true)
            setError(null)

            try {
                const mergedOptions = {
                    ...defaultOptions,
                    ...options,
                    headers: {
                        ...defaultOptions?.headers,
                        ...options.headers,
                    },
                }

                // Add abort signal to the request options
                const requestOptions = {
                    ...mergedOptions,
                    signal: abortController.signal,
                }

                // Now we can use the properly typed makeRequest without casting
                const result = await client.makeRequest(
                    endpoint,
                    requestOptions
                )

                // Only update state if request wasn't aborted
                if (!abortController.signal.aborted) {
                    setData(result as TResponse)
                    abortControllerRef.current = null
                }

                return result as TResponse
            } catch (err) {
                // Only update error state if request wasn't aborted
                if (!abortController.signal.aborted) {
                    const error =
                        err instanceof Error
                            ? err
                            : new Error('API call failed')
                    setError(error)
                    abortControllerRef.current = null
                    throw error
                }
                throw err
            } finally {
                // Only update loading state if request wasn't aborted
                if (!abortController.signal.aborted) {
                    setIsLoading(false)
                }
            }
        },
        [client, endpoint, defaultOptions, isLoading]
    )

    const reset = useCallback(() => {
        abort()
        setData(null)
        setError(null)
        setIsLoading(false)
    }, [abort])

    return {
        data,
        error,
        isLoading,
        call,
        reset,
        abort,
    }
}

/**
 * Hook for handling streaming responses from Ragbits endpoints
 * - Only predefined streaming routes are allowed
 * - Response type can be overridden with explicit type parameter
 * @param endpoint - The predefined streaming endpoint
 */
export function useRagbitsStream<TEndpoint extends StreamingEndpointPath>(
    endpoint: TEndpoint
): RagbitsStreamResult<Error, TEndpoint> {
    const { client } = useRagbitsContext()
    const [isStreaming, setIsStreaming] = useState(false)
    const [error, setError] = useState<Error | null>(null)
    const abortControllerRef = useRef<AbortController | null>(null)

    const cancel = useCallback(() => {
        if (!abortControllerRef.current) {
            return null
        }

        abortControllerRef.current.abort()
        abortControllerRef.current = null
        setIsStreaming(false)
    }, [])

    const stream = useCallback(
        (
            data: StreamingEndpointRequest<TEndpoint>,
            callbacks: StreamCallbacks<
                StreamingEndpointStream<TEndpoint>,
                string
            >
        ): (() => void) => {
            // Abort any existing stream only if there's one in progress
            if (abortControllerRef.current && isStreaming) {
                abortControllerRef.current.abort()
            }

            const abortController = new AbortController()
            abortControllerRef.current = abortController

            setError(null)
            setIsStreaming(true)

            const cancelFn = client.makeStreamRequest(
                endpoint,
                data,
                {
                    onMessage: callbacks.onMessage,
                    onError: (err: Error) => {
                        // Only update state if not aborted
                        if (!abortController.signal.aborted) {
                            setError(err)
                            setIsStreaming(false)

                            callbacks.onError(err.message)
                        }
                    },
                    onClose: () => {
                        // Only update state if not aborted
                        if (!abortController.signal.aborted) {
                            setIsStreaming(false)
                            // Ensure callbacks.onClose exists before calling it
                            if (callbacks.onClose) {
                                callbacks.onClose()
                            }
                        }
                    },
                },
                abortController.signal
            )

            return () => {
                cancel()
                cancelFn()
            }
        },
        [client, cancel, endpoint, isStreaming]
    )

    return {
        isStreaming,
        error,
        stream,
        cancel,
    }
}
