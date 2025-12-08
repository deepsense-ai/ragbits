import type {
    StreamCallbacks,
    RagbitsClient,
    RequestOptions,
    BaseApiEndpoints,
    EndpointRequest,
    EndpointResponse,
    BaseStreamingEndpoints,
    HasRequiredParams,
    AnyEndpoints,
} from '@ragbits/api-client'

// Re-export BaseApiEndpoints so it can be augmented via @ragbits/api-client-react
export type {
    BaseApiEndpoints,
    BaseStreamingEndpoints,
    EndpointDefinition,
} from '@ragbits/api-client'

/**
 * Call function type - mirrors makeRequest signature
 */
export type CallFunction<
    URL extends keyof Endpoints,
    Endpoints extends AnyEndpoints<Endpoints>,
> =
    HasRequiredParams<URL, Endpoints> extends true
        ? (
              options: RequestOptions<URL, Endpoints>
          ) => Promise<EndpointResponse<URL, Endpoints>>
        : (
              options?: RequestOptions<URL, Endpoints>
          ) => Promise<EndpointResponse<URL, Endpoints>>

// React-specific hook result types
export interface RagbitsCallResult<
    URL extends keyof Endpoints,
    Endpoints extends AnyEndpoints<Endpoints> = BaseApiEndpoints,
    Err = Error,
> {
    data: EndpointResponse<URL, Endpoints> | null
    error: Err | null
    isLoading: boolean
    call: CallFunction<URL, Endpoints>
    reset: () => void
    abort: () => void
}

export interface RagbitsStreamResult<
    URL extends keyof Endpoints,
    Endpoints extends AnyEndpoints<Endpoints> = BaseStreamingEndpoints,
    Err = Error,
> {
    isStreaming: boolean
    error: Err | null
    stream: (
        data: EndpointRequest<URL, Endpoints>,
        callbacks: StreamCallbacks<EndpointResponse<URL, Endpoints>, string>
    ) => () => void
    cancel: () => void
}

// Provider context type
export interface RagbitsContextValue {
    client: RagbitsClient
}
