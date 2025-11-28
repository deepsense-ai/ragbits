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

export interface EndpointDefinition<
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    Req = any,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
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
    Endpoints extends {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        [K in keyof Endpoints]: EndpointDefinition<any, any, any, any>
    },
> = keyof Endpoints

/**
 * Extract request type for a specific API endpoint
 */
export type EndpointRequest<
    URL extends keyof Endpoints,
    Endpoints extends {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        [K in keyof Endpoints]: EndpointDefinition<any, any, any, any>
    },
> = Endpoints[URL]['request']

/**
 * Extract response type for a specific API endpoint
 */
export type EndpointResponse<
    URL extends keyof Endpoints,
    Endpoints extends {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        [K in keyof Endpoints]: EndpointDefinition<any, any, any, any>
    },
> = Endpoints[URL]['response']

/**
 * Extract HTTP method for a specific API endpoint
 */
export type EndpointMethod<
    URL extends keyof Endpoints,
    Endpoints extends {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        [K in keyof Endpoints]: EndpointDefinition<any, any, any, any>
    },
> = Endpoints[URL]['method']

/**
 * Generic request options for API endpoints with typed methods, path params, query params, and body
 * - pathParams is REQUIRED when PathParams is not never
 * - queryParams is REQUIRED when it's a specific type (not never, not undefined)
 * - queryParams is OPTIONAL when it's never or undefined
 * - body is REQUIRED when it's a specific type (not never, not undefined)
 * - body is OPTIONAL when it's never or undefined
 */
export type RequestOptions<
    URL extends keyof Endpoints,
    Endpoints extends {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        [K in keyof Endpoints]: EndpointDefinition<any, any, any, any>
    },
> = {
    method?: Endpoints[URL]['method']
    headers?: Record<string, string>
    signal?: AbortSignal
} & (Endpoints[URL]['pathParams'] extends never
    ? { pathParams?: never }
    : { pathParams: Endpoints[URL]['pathParams'] }) &
    (Endpoints[URL]['queryParams'] extends never
        ? { queryParams?: never }
        : Endpoints[URL]['queryParams'] extends undefined
          ? { queryParams?: Endpoints[URL]['queryParams'] }
          : { queryParams: Endpoints[URL]['queryParams'] }) &
    (Endpoints[URL]['request'] extends never
        ? { body?: never }
        : Endpoints[URL]['request'] extends undefined
          ? { body?: Endpoints[URL]['request'] }
          : { body: Endpoints[URL]['request'] })

/**
 * Check if an endpoint has any required parameters
 * Returns true if any of these conditions are met:
 * - pathParams is not never, OR
 * - queryParams is not never AND not undefined, OR
 * - request/body is not never AND not undefined
 */
export type HasRequiredParams<
    URL extends keyof Endpoints,
    Endpoints extends {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        [K in keyof Endpoints]: EndpointDefinition<any, any, any, any>
    },
> = Endpoints[URL]['pathParams'] extends never
    ? Endpoints[URL]['queryParams'] extends never
        ? Endpoints[URL]['request'] extends never
            ? false
            : Endpoints[URL]['request'] extends undefined
              ? false
              : true // request is defined and not undefined -> required!
        : Endpoints[URL]['queryParams'] extends undefined
          ? Endpoints[URL]['request'] extends never
              ? false
              : Endpoints[URL]['request'] extends undefined
                ? false
                : true // request is defined and not undefined -> required!
          : true // queryParams is defined and not undefined -> required!
    : true // pathParams is defined -> required!

/**
 * Conditional options parameter for makeRequest
 * - Required if endpoint has:
 *   - pathParams, OR
 *   - queryParams with specific type (not undefined), OR
 *   - body with specific type (not undefined)
 * - Optional otherwise
 */
export type MakeRequestOptions<
    URL extends keyof Endpoints,
    Endpoints extends {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        [K in keyof Endpoints]: EndpointDefinition<any, any, any, any>
    },
> =
    HasRequiredParams<URL, Endpoints> extends true
        ? [options: RequestOptions<URL, Endpoints>]
        : [options?: RequestOptions<URL, Endpoints>]
