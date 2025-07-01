import { RJSFSchema } from '@rjsf/utils'

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
    LIVE_UPDATE = 'live_update',
    FOLLOWUP_MESSAGES = 'followup_messages',
}

/**
 * Feedback types for user feedback
 */
export enum FeedbackType {
    LIKE = 'like',
    DISLIKE = 'dislike',
}

/**
 * Server state interface for state updates
 */
export interface ServerState {
    state: Record<string, unknown>
    signature: string
}

export enum LiveUpdateType {
    START = 'START',
    FINISH = 'FINISH',
}

export interface LiveUpdate {
    update_id: string
    type: LiveUpdateType
    content: {
        label: string
        description?: string
    }
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

interface LiveUpdateChatResponse {
    type: ChatResponseType.LIVE_UPDATE
    content: LiveUpdate
}

interface FollowupMessagesChatResponse {
    type: ChatResponseType.FOLLOWUP_MESSAGES
    content: string[]
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
    | LiveUpdateChatResponse
    | FollowupMessagesChatResponse

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
    feedback: FeedbackType
    payload: Record<string, unknown> | null
}

/**
 * Feedback response from the API
 */
export interface FeedbackResponse {
    status: string
}

/**
 * UI customization configuration
 */
export interface UICustomization {
    header: {
        title?: string
        subtitle?: string
        logo?: string
    }
    welcome_message?: string
}

/**
 * Configuration response from the API
 */
export interface ConfigResponse {
    feedback: {
        like: {
            enabled: boolean
            form: RJSFSchema | null
        }
        dislike: {
            enabled: boolean
            form: RJSFSchema | null
        }
    }
    customization: UICustomization | null
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

export interface EndpointDefinition<Req = unknown, Res = unknown> {
    method: string
    request: Req
    response: Res
}

/**
 * Base predefined API endpoint definitions with their request/response types
 */
export type BaseApiEndpoints = {
    '/api/config': EndpointDefinition<never, ConfigResponse>
    '/api/feedback': EndpointDefinition<FeedbackRequest, FeedbackResponse>
}

/**
 * Streaming API endpoint definitions with their request/stream response types
 */
export type BaseStreamingEndpoints = {
    '/api/chat': EndpointDefinition<ChatRequest, TypedChatResponse>
}

/**
 * Extract endpoint paths as a union type
 */
export type EndpointPath<Endpoints extends Record<string, EndpointDefinition>> =
    keyof Endpoints

/**
 * Extract request type for a specific API endpoint
 */
export type EndpointRequest<
    Url extends keyof Endpoints,
    Endpoints extends Record<string, EndpointDefinition>,
> = Endpoints[Url]['request']

/**
 * Extract response type for a specific API endpoint
 */
export type EndpointResponse<
    Url extends keyof Endpoints,
    Endpoints extends Record<string, EndpointDefinition>,
> = Endpoints[Url]['response']

/**
 * Extract HTTP method for a specific API endpoint
 */
export type EndpointMethod<
    Url extends keyof Endpoints,
    Endpoints extends Record<string, EndpointDefinition>,
> = Endpoints[Url]['method']

/**
 * Generic request options for API endpoints with typed methods and body
 */
export interface TypedRequestOptions<
    T extends keyof E,
    E extends Record<string, EndpointDefinition>,
> {
    method?: E[T]['method']
    body?: E[T]['request'] extends never ? undefined : E[T]['request']
    headers?: Record<string, string>
    signal?: AbortSignal
}
