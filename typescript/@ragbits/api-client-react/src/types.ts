import type {
    StreamCallbacks,
    RagbitsClient,
    TypedRequestOptions,
    EndpointDefinition,
    BaseApiEndpoints,
    EndpointRequest,
    EndpointResponse,
} from '@ragbits/api-client'

// React-specific hook result types
export interface RagbitsCallResult<
    Url extends keyof Endpoints,
    Endpoints extends Record<string, EndpointDefinition> = BaseApiEndpoints,
    Err = Error,
> {
    data: EndpointResponse<Url, Endpoints> | null
    error: Err | null
    isLoading: boolean
    call: (
        options?: TypedRequestOptions<Url, Endpoints>
    ) => Promise<EndpointResponse<Url, Endpoints>>
    reset: () => void
    abort: () => void
}

export interface RagbitsStreamResult<
    Url extends keyof Endpoints,
    Endpoints extends Record<string, EndpointDefinition> = BaseApiEndpoints,
    Err = Error,
> {
    isStreaming: boolean
    error: Err | null
    stream: (
        data: EndpointRequest<Url, Endpoints>,
        callbacks: StreamCallbacks<EndpointResponse<Url, Endpoints>, string>
    ) => () => void
    cancel: () => void
}

// Provider context type
export interface RagbitsContextValue {
    client: RagbitsClient
}
