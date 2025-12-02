import { useState, useCallback, useRef } from 'react'
import type {
    StreamCallbacks,
    EndpointResponse,
    RequestOptions,
    EndpointDefinition,
    BaseApiEndpoints,
    EndpointRequest,
    BaseStreamingEndpoints,
    MakeRequestOptions,
} from '@ragbits/api-client'
import type {
    RagbitsCallResult,
    RagbitsStreamResult,
    CallFunction,
} from './types'
import { useRagbitsContext } from './RagbitsContextProvider'

/**
 * Hook for making API calls to Ragbits endpoints
 * - Supports any endpoints by providing `Endpoints` generic argument
 * @param endpoint - The predefined API endpoint
 * @param defaultOptions - Default options for the API call
 */
export function useRagbitsCall<
    Endpoints extends {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        [K in keyof Endpoints]: EndpointDefinition<any, any, any, any>
    } = BaseApiEndpoints,
    URL extends keyof Endpoints = keyof Endpoints,
>(
    endpoint: URL,
    defaultOptions?: Partial<RequestOptions<URL, Endpoints>>
): RagbitsCallResult<URL, Endpoints, Error> {
    const { client } = useRagbitsContext()
    const [data, setData] = useState<EndpointResponse<URL, Endpoints> | null>(
        null
    )
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
            ...args: MakeRequestOptions<URL, Endpoints>
        ): Promise<EndpointResponse<URL, Endpoints>> => {
            const options = args[0]

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
                    ...(options || {}),
                    headers: {
                        ...defaultOptions?.headers,
                        ...(options?.headers || {}),
                    },
                }

                // Add abort signal to the request options
                const requestOptions = {
                    ...mergedOptions,
                    signal: abortController.signal,
                } as RequestOptions<URL, Endpoints>

                // Now we can use the properly typed makeRequest
                const result = await client.makeRequest<Endpoints>(
                    endpoint,
                    requestOptions
                )

                // Only update state if request wasn't aborted
                if (!abortController.signal.aborted) {
                    setData(result)
                    abortControllerRef.current = null
                }

                return result
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
    ) as CallFunction<URL, Endpoints>

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
 * - Supports any streaming endpoints by providing `Endpoints` generic argument
 * @param endpoint - The predefined streaming endpoint
 */
export function useRagbitsStream<
    Endpoints extends {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        [K in keyof Endpoints]: EndpointDefinition<any, any, any, any>
    } = BaseStreamingEndpoints,
    URL extends keyof Endpoints = keyof Endpoints,
>(
    endpoint: URL,
    customHeaders?: Record<string, string>
): RagbitsStreamResult<URL, Endpoints, Error> {
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
            data: EndpointRequest<URL, Endpoints>,
            callbacks: StreamCallbacks<EndpointResponse<URL, Endpoints>, string>
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
                abortController.signal,
                customHeaders
            )

            return () => {
                cancel()
                cancelFn()
            }
        },
        [isStreaming, client, endpoint, customHeaders, cancel]
    )

    return {
        isStreaming,
        error,
        stream,
        cancel,
    }
}
