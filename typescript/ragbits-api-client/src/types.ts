/**
 * Message roles for chat conversations
 */
export enum MessageRole {
    USER = 'user',
    ASSISTANT = 'assistant',
    SYSTEM = 'system',
}

/**
 * Message structure for chat conversations
 */
export interface Message {
    role: MessageRole
    content: string
    id?: string
}

/**
 * Reference structure for document references
 */
export interface Reference {
    title: string
    content: string
    url?: string
}

/**
 * Response types from the API
 */
export enum ChatResponseType {
    MESSAGE = 'message',
    REFERENCE = 'reference',
    STATE_UPDATE = 'state_update',
    TEXT = 'text',
    MESSAGE_ID = 'message_id',
    CONVERSATION_ID = 'conversation_id',
}

/**
 * Server state interface for state updates
 */
export interface ServerState {
    state: Record<string, unknown>
    signature: string
}

/**
 * Specific chat response types
 */
interface MessageIdChatResponse {
    type: ChatResponseType.MESSAGE_ID
    content: string
}

interface TextChatResponse {
    type: ChatResponseType.TEXT
    content: string
}

interface ReferenceChatResponse {
    type: ChatResponseType.REFERENCE
    content: Reference
}

interface ConversationIdChatResponse {
    type: ChatResponseType.CONVERSATION_ID
    content: string
}

interface StateUpdateChatResponse {
    type: ChatResponseType.STATE_UPDATE
    content: ServerState
}

/**
 * Typed chat response union
 */
export type TypedChatResponse =
    | TextChatResponse
    | ReferenceChatResponse
    | MessageIdChatResponse
    | ConversationIdChatResponse
    | StateUpdateChatResponse

/**
 * Base chat request to the API
 */
export interface ChatRequest {
    message: string
    history: Message[]
    context?: Record<string, unknown>
}

/**
 * Feedback request to the API
 */
export interface FeedbackRequest {
    message_id: string
    // TODO: add type
    feedback: any
    payload: Record<string, unknown> | null
}

/**
 * Feedback response from the API
 */
export interface FeedbackResponse {
    status: string
}

/**
 * Form field response structure
 */
export interface FormFieldResponse {
    name: string
    label: string
    // TODO: add type
    type: any
    required: boolean
    options?: string[]
}

/**
 * Form schema response structure
 */
export interface FormSchemaResponse {
    title: string
    fields: FormFieldResponse[]
}

/**
 * Configuration response from the API
 */
export interface ConfigResponse {
    feedback: {
        like: {
            enabled: boolean
            form: FormSchemaResponse | null
        }
        dislike: {
            enabled: boolean
            form: FormSchemaResponse | null
        }
    }
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

/**
 * Regular API endpoint definitions with their request/response types
 */
export interface ApiEndpoints {
    '/api/config': {
        method: 'GET'
        request: never
        response: ConfigResponse
    }
    '/api/feedback': {
        method: 'POST'
        request: FeedbackRequest
        response: FeedbackResponse
    }
}

/**
 * Streaming API endpoint definitions with their request/stream response types
 */
export interface StreamingEndpoints {
    '/api/chat': {
        method: 'POST'
        request: ChatRequest
        stream: TypedChatResponse
    }
}

/**
 * Extract endpoint paths as a union type
 */
export type ApiEndpointPath = keyof ApiEndpoints

/**
 * Extract streaming endpoint paths as a union type
 */
export type StreamingEndpointPath = keyof StreamingEndpoints

/**
 * Extract request type for a specific API endpoint
 */
export type ApiEndpointRequest<T extends ApiEndpointPath> =
    ApiEndpoints[T]['request']

/**
 * Extract response type for a specific API endpoint
 */
export type ApiEndpointResponse<T extends ApiEndpointPath> =
    ApiEndpoints[T]['response']

/**
 * Extract HTTP method for a specific API endpoint
 */
export type ApiEndpointMethod<T extends ApiEndpointPath> =
    ApiEndpoints[T]['method']

/**
 * Extract request type for a specific streaming endpoint
 */
export type StreamingEndpointRequest<T extends StreamingEndpointPath> =
    StreamingEndpoints[T]['request']

/**
 * Extract stream response type for a specific streaming endpoint
 */
export type StreamingEndpointStream<T extends StreamingEndpointPath> =
    StreamingEndpoints[T]['stream']

/**
 * Extract HTTP method for a specific streaming endpoint
 */
export type StreamingEndpointMethod<T extends StreamingEndpointPath> =
    StreamingEndpoints[T]['method']

/**
 * Generic request options for API endpoints with typed methods and body
 */
export interface TypedApiRequestOptions<T extends ApiEndpointPath> {
    method?: ApiEndpointMethod<T>
    body?: ApiEndpointRequest<T> extends never
        ? undefined
        : ApiEndpointRequest<T>
    headers?: Record<string, string>
    signal?: AbortSignal
}

/**
 * Typed request options for specific streaming endpoints
 */
export interface TypedStreamRequestOptions<T extends StreamingEndpointPath> {
    method?: StreamingEndpointMethod<T>
    body?: StreamingEndpointRequest<T>
    headers?: Record<string, string>
    signal?: AbortSignal
}
