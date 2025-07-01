import type {
    StreamCallbacks,
    RagbitsClient,
    TypedRequestOptions,
    EndpointDefinition,
    BaseApiEndpoints,
    EndpointRequest,
    EndpointResponse,
    BaseStreamingEndpoints,
} from '@ragbits/api-client'

// React-specific hook result types
export interface RagbitsCallResult<
    URL extends keyof Endpoints,
    Endpoints extends {
        [K in keyof Endpoints]: EndpointDefinition
    } = BaseApiEndpoints,
    Err = Error,
> {
    data: EndpointResponse<URL, Endpoints> | null
    error: Err | null
    isLoading: boolean
    call: (
        options?: TypedRequestOptions<URL, Endpoints>
    ) => Promise<EndpointResponse<URL, Endpoints>>
    reset: () => void
    abort: () => void
}

export interface RagbitsStreamResult<
    URL extends keyof Endpoints,
    Endpoints extends {
        [K in keyof Endpoints]: EndpointDefinition
    } = BaseStreamingEndpoints,
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
