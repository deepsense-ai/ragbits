import {
    ConfigResponse,
    FeedbackRequest,
    FeedbackResponse,
    ChatRequest,
    ChatResponse,
    LogoutRequest,
    LoginRequest,
    LoginResponse,
} from './autogen.types'

export interface GenericResponse {
    success: boolean
}

/**
 * Configuration for the client
 */
export interface ClientConfig {
    baseUrl?: string
    auth?: {
        getToken?: () => string
        onUnauthorized?: () => Promise<void> | void
    }
}

/**
 * Callbacks for handling streaming responses
 */
export interface StreamCallbacks<T, E = Error> {
    onMessage: (data: T) => void | Promise<void>
    onError: (error: E) => void | Promise<void>
    onClose?: () => void | Promise<void>
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export interface EndpointDefinition<
    Req = any,
    Res = any,
    PathParams = never,
    QueryParams = never,
> {
    method: string
    request: Req
    response: Res
    pathParams: PathParams
    queryParams: QueryParams
}

/**
 * Base predefined API endpoint definitions with their request/response types
 */
export interface BaseApiEndpoints {
    '/api/config': EndpointDefinition<never, ConfigResponse>
    '/api/feedback': EndpointDefinition<FeedbackRequest, FeedbackResponse>
    '/api/auth/login': EndpointDefinition<LoginRequest, LoginResponse>
    '/api/auth/logout': EndpointDefinition<LogoutRequest, GenericResponse>
    '/api/theme': EndpointDefinition<never, string>
}

/**
 * Streaming API endpoint definitions with their request/stream response types
 */
export interface BaseStreamingEndpoints {
    '/api/chat': EndpointDefinition<ChatRequest, ChatResponse>
}

/**
 * Extract endpoint paths as a union type
 */
export type EndpointPath<
    Endpoints extends { [K in keyof Endpoints]: EndpointDefinition },
> = keyof Endpoints

/**
 * Extract request type for a specific API endpoint
 */
export type EndpointRequest<
    URL extends keyof Endpoints,
    Endpoints extends { [K in keyof Endpoints]: EndpointDefinition },
> = Endpoints[URL]['request']

/**
 * Extract response type for a specific API endpoint
 */
export type EndpointResponse<
    URL extends keyof Endpoints,
    Endpoints extends { [K in keyof Endpoints]: EndpointDefinition },
> = Endpoints[URL]['response']

/**
 * Extract HTTP method for a specific API endpoint
 */
export type EndpointMethod<
    URL extends keyof Endpoints,
    Endpoints extends { [K in keyof Endpoints]: EndpointDefinition },
> = Endpoints[URL]['method']

/**
 * Generic request options for API endpoints with typed methods, body, path params, and query params
 */
export interface RequestOptions<
    URL extends keyof Endpoints,
    Endpoints extends { [K in keyof Endpoints]: EndpointDefinition },
> {
    method?: Endpoints[URL]['method']
    body?: Endpoints[URL]['request'] extends never
        ? undefined
        : Endpoints[URL]['request']
<<<<<<< Updated upstream
=======
    pathParams?: Endpoints[URL]['pathParams'] extends never
        ? never
        : Endpoints[URL]['pathParams']
    queryParams?: Endpoints[URL]['queryParams'] extends never
        ? never
        : Endpoints[URL]['queryParams']
>>>>>>> Stashed changes
    headers?: Record<string, string>
    signal?: AbortSignal
}
