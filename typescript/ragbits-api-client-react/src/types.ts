import type {
    StreamCallbacks,
    RagbitsClient,
    StreamingEndpointPath,
    StreamingEndpointRequest,
    TypedApiRequestOptions,
    ApiEndpointPath,
    StreamingEndpointStream,
} from '@ragbits/api-client'

// React-specific hook result types
export interface RagbitsCallResult<
    T,
    E = Error,
    TEndpoint extends ApiEndpointPath = ApiEndpointPath,
> {
    data: T | null
    error: E | null
    isLoading: boolean
    call: (options?: TypedApiRequestOptions<TEndpoint>) => Promise<T>
    reset: () => void
    abort: () => void
}

export interface RagbitsStreamResult<
    E = Error,
    TEndpoint extends StreamingEndpointPath = StreamingEndpointPath,
> {
    isStreaming: boolean
    error: E | null
    stream: (
        data: StreamingEndpointRequest<TEndpoint>,
        callbacks: StreamCallbacks<StreamingEndpointStream<TEndpoint>, string>
    ) => () => void
    cancel: () => void
}

// Provider context type
export interface RagbitsContextValue {
    client: RagbitsClient
}
