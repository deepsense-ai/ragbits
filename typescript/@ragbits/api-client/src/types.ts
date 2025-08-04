import {
    ConfigResponse,
    FeedbackRequest,
    FeedbackResponse,
    ChatRequest,
    ChatResponse,
} from './autogen.types'

export interface User {
    user_id: string
    username: string
    email: string | null
    full_name: string | null
    roles: string[]
    metadata: Record<string, unknown>
}

export interface JWTToken {
    access_token: string
    token_type: string
    expires_in: number
    refresh_token: string | null
    user: User
}

export interface LoginRequest {
    username: string
    password: string
}

export interface LoginResponse {
    success: boolean
    user: User | null
    error_message: string | null
    jwt_token: JWTToken | null
}

export interface LogoutRequest {
    session_id: string
}

export interface LogoutResponse {
    success: boolean
}
/**
 * Configuration for the client
 */
export interface ClientConfig {
    baseUrl?: string
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
export interface EndpointDefinition<Req = any, Res = any> {
    method: string
    request: Req
    response: Res
}

/**
 * Base predefined API endpoint definitions with their request/response types
 */
export interface BaseApiEndpoints {
    '/api/config': EndpointDefinition<never, ConfigResponse>
    '/api/feedback': EndpointDefinition<FeedbackRequest, FeedbackResponse>
    '/api/auth/login': EndpointDefinition<LoginRequest, LoginResponse>
    '/api/auth/logout': EndpointDefinition<LogoutRequest, LogoutResponse>
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
 * Generic request options for API endpoints with typed methods and body
 */
export interface RequestOptions<
    URL extends keyof Endpoints,
    Endpoints extends { [K in keyof Endpoints]: EndpointDefinition },
> {
    method?: Endpoints[URL]['method']
    body?: Endpoints[URL]['request'] extends never
        ? undefined
        : Endpoints[URL]['request']
    headers?: Record<string, string>
    signal?: AbortSignal
}
