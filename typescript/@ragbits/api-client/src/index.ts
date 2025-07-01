import type {
    ClientConfig,
    StreamCallbacks,
    BaseApiEndpoints,
    EndpointDefinition,
    EndpointResponse,
    TypedRequestOptions,
    BaseStreamingEndpoints,
    EndpointRequest,
} from './types'

/**
 * Client for communicating with the Ragbits API
 */
export class RagbitsClient {
    private readonly baseUrl: string

    /**
     * @param config - Configuration object
     */
    constructor(config: ClientConfig = {}) {
        this.baseUrl = config.baseUrl || 'http://127.0.0.1:8000'

        // Validate the base URL
        try {
            new URL(this.baseUrl)
        } catch {
            throw new Error(
                `Invalid base URL: ${this.baseUrl}. Please provide a valid URL.`
            )
        }

        if (this.baseUrl.endsWith('/')) {
            this.baseUrl = this.baseUrl.slice(0, -1)
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
     * @param endpoint - API endpoint path (must be predefined)
     * @param options - Typed request options for the specific endpoint
     */
    async makeRequest<
        Url extends keyof Endpoints extends string ? keyof Endpoints : never,
        Endpoints extends Record<string, EndpointDefinition> = BaseApiEndpoints,
    >(
        endpoint: Url,
        options?: TypedRequestOptions<Url, Endpoints>
    ): Promise<EndpointResponse<Url, Endpoints>> {
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
            this._buildApiUrl(endpoint),
            requestOptions
        )
        return response.json()
    }

    /**
     * Method for streaming requests to known endpoints only
     * @param endpoint - Streaming endpoint path (must be predefined)
     * @param data - Request data
     * @param callbacks - Stream callbacks
     * @param signal - Optional AbortSignal for cancelling the request
     */
    makeStreamRequest<
        Url extends keyof Endpoints extends string ? keyof Endpoints : never,
        Endpoints extends Record<
            string,
            EndpointDefinition
        > = BaseStreamingEndpoints,
    >(
        endpoint: Url,
        data: EndpointRequest<Url, Endpoints>,
        callbacks: StreamCallbacks<EndpointResponse<Url, Endpoints>>,
        signal?: AbortSignal
    ): () => void {
        let isCancelled = false

        const processStream = async (response: Response): Promise<void> => {
            const reader = response.body
                ?.pipeThrough(new TextDecoderStream())
                .getReader()

            if (!reader) {
                throw new Error('Response body is null')
            }

            while (!isCancelled && !signal?.aborted) {
                try {
                    const { value, done } = await reader.read()
                    if (done) {
                        callbacks.onClose?.()
                        break
                    }

                    const lines = value.split('\n')
                    for (const line of lines) {
                        if (!line.startsWith('data: ')) continue

                        try {
                            const jsonString = line.replace('data: ', '').trim()
                            const parsedData = JSON.parse(
                                jsonString
                            ) as EndpointResponse<Url, Endpoints>
                            await callbacks.onMessage(parsedData)
                        } catch (parseError) {
                            console.error('Error parsing JSON:', parseError)
                            await callbacks.onError(
                                new Error('Error processing server response')
                            )
                        }
                    }
                } catch (streamError) {
                    console.error('Stream error:', streamError)
                    await callbacks.onError(new Error('Error reading stream'))
                    break
                }
            }
        }

        const startStream = async (): Promise<void> => {
            try {
                const response = await fetch(this._buildApiUrl(endpoint), {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        Accept: 'text/event-stream',
                    },
                    body: JSON.stringify(data),
                    signal,
                })

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
}

// Re-export types
export * from './types'
