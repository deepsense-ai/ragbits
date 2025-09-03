import { ChatResponseType, ChunkedChatResponse, Image } from './autogen.types'
import type {
    ClientConfig,
    StreamCallbacks,
    BaseApiEndpoints,
    EndpointDefinition,
    EndpointResponse,
    RequestOptions,
    BaseStreamingEndpoints,
    EndpointRequest,
} from './types'

/**
 * Client for communicating with the Ragbits API
 */
export class RagbitsClient {
    private readonly baseUrl: string
    private imageChunks: Map<
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
        const defaultOptions: RequestInit = {
            headers: {
                'Content-Type': 'application/json',
            },
        }

        const response = await fetch(url, { ...defaultOptions, ...options })
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
            [K in keyof Endpoints]: EndpointDefinition
        } = BaseApiEndpoints,
        URL extends keyof Endpoints = keyof Endpoints,
    >(
        endpoint: URL,
        options?: RequestOptions<URL, Endpoints>
    ): Promise<EndpointResponse<URL, Endpoints>> {
        const {
            method = 'GET',
            body,
            headers = {},
            ...restOptions
        } = options || {}

        const requestOptions: RequestInit = {
            method,
            headers,
            ...restOptions, // This will include signal and other fetch options
        }

        if (body && method !== 'GET') {
            requestOptions.body =
                typeof body === 'string' ? body : JSON.stringify(body)
        }

        const response = await this._makeRequest(
            this._buildApiUrl(endpoint.toString()),
            requestOptions
        )
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
            [K in keyof Endpoints]: EndpointDefinition
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

                            if (
                                parsedData.type ===
                                ChatResponseType.ChunkedContent
                            ) {
                                this.handleChunkedContent(parsedData, callbacks)
                                continue
                            }

                            await callbacks.onMessage(parsedData)
                        } catch (parseError) {
                            console.error('Error parsing JSON:', parseError)
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
                const response = await fetch(
                    this._buildApiUrl(endpoint.toString()),
                    {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            Accept: 'text/event-stream',
                            ...customHeaders,
                        },
                        body: JSON.stringify(data),
                        signal,
                    }
                )

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

    private async handleChunkedContent<T>(
        data: T,
        callbacks: StreamCallbacks<T>
    ): Promise<void> {
        const response = data as ChunkedChatResponse
        const content = response.content
        const contentType = content.content_type
        const id = content.id
        const chunkIndex = content.chunk_index
        const totalChunks = content.total_chunks
        const mimeType = content.mime_type

        // The chunk data is now in the _data field
        const chunkData = content.data

        // Initialize chunk storage if needed
        if (!this.imageChunks.has(id)) {
            this.imageChunks.set(id, {
                chunks: new Map(),
                totalChunks,
                mimeType,
            })
        }

        // Store the chunk
        const imageInfo = this.imageChunks.get(id)!
        imageInfo.chunks.set(chunkIndex, chunkData)

        // Check if all chunks are received
        if (imageInfo.chunks.size === totalChunks) {
            // Reconstruct the complete data
            const sortedChunks = Array.from({ length: totalChunks }, (_, i) =>
                imageInfo.chunks.get(i)
            )

            const completeBase64 = sortedChunks.join('')

            // Validate the base64 data
            try {
                atob(completeBase64)
            } catch (e) {
                this.imageChunks.delete(id)
                console.error('❌ Invalid base64 data: ', e)
                await callbacks.onError(new Error('Error reading stream'))
            }

            if (contentType === ChatResponseType.Image) {
                // Create the complete image response
                const completeImageResponse: {
                    type: typeof ChatResponseType.Image
                    content: Image
                } = {
                    type: ChatResponseType.Image,
                    content: {
                        id: id,
                        url: `${imageInfo.mimeType},${completeBase64}`,
                    },
                }
                // Send the complete image
                await callbacks.onMessage(completeImageResponse as T)
            }
        }
    }
}

// Re-export types
export * from './types'
export * from './autogen.types'
