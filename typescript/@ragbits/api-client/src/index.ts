import { ChunkedChatResponse, Image } from './autogen.types'
import type {
    ClientConfig,
    StreamCallbacks,
    BaseApiEndpoints,
    EndpointDefinition,
    EndpointResponse,
    BaseStreamingEndpoints,
    EndpointRequest,
    MakeRequestOptions,
} from './types'

/**
 * Client for communicating with the Ragbits API
 */
export class RagbitsClient {
    private readonly baseUrl: string
    private readonly auth: ClientConfig['auth']
    private chunkQueue: Map<
        string,
        {
            chunks: Map<number, string>
            totalChunks: number
            mimeType: string
        }
    > = new Map()

    /**
     * @param config - Configuration object
     */
    constructor(config: ClientConfig = {}) {
        this.baseUrl = config.baseUrl ?? ''
        this.auth = config.auth

        if (this.baseUrl.endsWith('/')) {
            this.baseUrl = this.baseUrl.slice(0, -1)
        }

        if (!this.baseUrl) {
            return
        }

        // Validate the base URL if given
        try {
            new URL(this.baseUrl)
        } catch {
            throw new Error(
                `Invalid base URL: ${this.baseUrl}. Please provide a valid URL.`
            )
        }
    }

    /**
     * Get the base URL used by this client
     */
    getBaseUrl(): string {
        return this.baseUrl
    }

    /**
     * Build full API URL from path
     * @private
     */
    private _buildApiUrl(path: string): string {
        return `${this.baseUrl}${path}`
    }

    /**
     * Make a request to the API
     * @private
     */
    private async _makeRequest(
        url: string,
        options: RequestInit = {}
    ): Promise<Response> {
        const defaultHeaders: Record<string, string> = {
            'Content-Type': 'application/json',
        }

        const headers = {
            ...defaultHeaders,
            ...this.normalizeHeaders(options.headers),
        }

        if (this.auth?.getToken) {
            headers['Authorization'] = `Bearer ${this.auth.getToken()}`
        }

        const response = await fetch(url, { ...options, headers })

        if (response.status === 401) {
            this.auth?.onUnauthorized?.()
        }

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`)
        }
        return response
    }

    /**
     * Method to make API requests to known endpoints only
     * @param endpoint - API endpoint path
     * @param options - Typed request options for the specific endpoint
     */
    async makeRequest<
        Endpoints extends {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            [K in keyof Endpoints]: EndpointDefinition<any, any, any, any>
        } = BaseApiEndpoints,
        URL extends keyof Endpoints = keyof Endpoints,
    >(
        endpoint: URL,
        ...args: MakeRequestOptions<URL, Endpoints>
    ): Promise<EndpointResponse<URL, Endpoints>> {
        const options = args[0]

        const {
            method = 'GET',
            body,
            pathParams,
            queryParams,
            headers = {},
            ...restOptions
        } = options || {}

        const requestOptions: RequestInit = {
            method,
            headers,
            ...restOptions,
        }

        if (body && method !== 'GET') {
            requestOptions.body =
                typeof body === 'string' ? body : JSON.stringify(body)
        }

        // Build URL with path parameters
        let url = endpoint.toString()

        // Replace path parameters (e.g., :id, :userId)
        if (pathParams) {
            url = url.replace(/:([^/]+)/g, (_, paramName) => {
                if (paramName in pathParams) {
                    const value = (pathParams as Record<string, unknown>)[
                        paramName
                    ]
                    return encodeURIComponent(String(value))
                } else {
                    throw new Error(`Path parameter ${paramName} is required`)
                }
            })
        }

        // Add query parameters
        if (queryParams && Object.keys(queryParams).length > 0) {
            const searchParams = new URLSearchParams()
            for (const [key, value] of Object.entries(queryParams)) {
                if (value !== undefined && value !== null) {
                    searchParams.append(key, String(value))
                }
            }
            url += `?${searchParams.toString()}`
        }

        url = this._buildApiUrl(url)

        const response = await this._makeRequest(url, requestOptions)
        return response.json()
    }

    /**
     * Method for streaming requests to known endpoints only
     * @param endpoint - Streaming endpoint path
     * @param data - Request data
     * @param callbacks - Stream callbacks
     * @param signal - Optional AbortSignal for cancelling the request
     */
    makeStreamRequest<
        Endpoints extends {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            [K in keyof Endpoints]: EndpointDefinition<any, any, any, any>
        } = BaseStreamingEndpoints,
        URL extends keyof Endpoints = keyof Endpoints,
    >(
        endpoint: URL,
        data: EndpointRequest<URL, Endpoints>,
        callbacks: StreamCallbacks<EndpointResponse<URL, Endpoints>>,
        signal?: AbortSignal,
        customHeaders?: Record<string, string>
    ): () => void {
        let isCancelled = false

        const processStream = async (response: Response): Promise<void> => {
            const reader = response.body
                ?.pipeThrough(new TextDecoderStream())
                .getReader()

            if (!reader) {
                throw new Error('Response body is null')
            }

            let buffer = ''

            while (!isCancelled && !signal?.aborted) {
                try {
                    const { value, done } = await reader.read()
                    if (done) {
                        callbacks.onClose?.()
                        break
                    }

                    buffer += value
                    const lines = buffer.split('\n')
                    buffer = lines.pop() ?? ''

                    for (const line of lines) {
                        if (!line.startsWith('data: ')) continue

                        try {
                            const jsonString = line.replace('data: ', '').trim()

                            const parsedData = JSON.parse(
                                jsonString
                            ) as EndpointResponse<URL, Endpoints>

                            if (parsedData.type === 'chunked_content') {
                                this.handleChunkedContent(parsedData, callbacks)
                                continue
                            }

                            await callbacks.onMessage(parsedData)
                        } catch (parseError) {
                            console.error('Error parsing JSON:', parseError)
                            await callbacks.onError(
                                new Error('Error processing server response')
                            )
                        }
                    }
                } catch (streamError) {
                    if (signal?.aborted) {
                        return
                    }
                    console.error('Stream error:', streamError)
                    await callbacks.onError(new Error('Error reading stream'))
                    break
                }
            }
        }

        const startStream = async (): Promise<void> => {
            try {
                const defaultHeaders: Record<string, string> = {
                    'Content-Type': 'application/json',
                    Accept: 'text/event-stream',
                }

                const headers = {
                    ...defaultHeaders,
                    ...customHeaders,
                }

                if (this.auth?.getToken) {
                    headers['Authorization'] = `Bearer ${this.auth.getToken()}`
                }

                const response = await fetch(
                    this._buildApiUrl(endpoint.toString()),
                    {
                        method: 'POST',
                        headers,
                        body: JSON.stringify(data),
                        signal,
                    }
                )

                if (response.status === 401) {
                    this.auth?.onUnauthorized?.()
                }

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`)
                }

                await processStream(response)
            } catch (error) {
                if (signal?.aborted) {
                    return
                }

                console.error('Request error:', error)
                const errorMessage =
                    error instanceof Error
                        ? error.message
                        : 'Error connecting to server'
                await callbacks.onError(new Error(errorMessage))
            }
        }

        try {
            startStream()
        } catch (error) {
            const errorMessage =
                error instanceof Error
                    ? error.message
                    : 'Failed to start stream'
            callbacks.onError(new Error(errorMessage))
        }

        return () => {
            isCancelled = true
        }
    }

    private normalizeHeaders(init?: HeadersInit): Record<string, string> {
        if (!init) return {}
        if (init instanceof Headers) {
            return Object.fromEntries(init.entries())
        }
        if (Array.isArray(init)) {
            return Object.fromEntries(init)
        }
        return init
    }

    private async handleChunkedContent<T>(
        data: T,
        callbacks: StreamCallbacks<T>
    ): Promise<void> {
        const response = data as ChunkedChatResponse
        const content = response.content

        const {
            content_type: contentType,
            id,
            chunk_index: chunkIndex,
            total_chunks: totalChunks,
            mime_type: mimeType,
            data: chunkData,
        } = content

        // Initialize chunk storage if needed
        if (!this.chunkQueue.has(id)) {
            this.chunkQueue.set(id, {
                chunks: new Map(),
                totalChunks,
                mimeType,
            })
        }

        // Store the chunk
        const imageInfo = this.chunkQueue.get(id)!
        imageInfo.chunks.set(chunkIndex, chunkData)

        // Check if all chunks are received
        if (imageInfo.chunks.size !== totalChunks) return

        // Reconstruct the complete data
        const sortedChunks = Array.from({ length: totalChunks }, (_, i) =>
            imageInfo.chunks.get(i)
        )

        const completeBase64 = sortedChunks.join('')

        // Validate the base64 data
        try {
            atob(completeBase64)
        } catch (e) {
            this.chunkQueue.delete(id)
            console.error('❌ Invalid base64 data: ', e)
            await callbacks.onError(new Error('Error reading stream'))
        }

        if (contentType === 'image') {
            // Create the complete image response
            const completeImageResponse: {
                type: 'image'
                content: Image
            } = {
                type: 'image',
                content: {
                    id: id,
                    url: `${imageInfo.mimeType},${completeBase64}`,
                },
            }
            // Send the complete image
            await callbacks.onMessage(completeImageResponse as T)
        }

        this.chunkQueue.delete(id)
    }
}

// Re-export types
export * from './types'
export * from './autogen.types'
