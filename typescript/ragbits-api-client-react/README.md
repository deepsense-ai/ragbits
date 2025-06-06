# Ragbits API Client React

React hooks for the Ragbits API client. This package provides React-friendly hooks built on top of the core `ragbits-api-client` package.

## Installation

```bash
npm install ragbits-api-client-react
```

Note: This package depends on `ragbits-api-client` which will be installed automatically.

## Usage

### Setup Provider

First, wrap your app with the `RagbitsProvider`:

```tsx
import { RagbitsProvider } from 'ragbits-api-client-react'

function App() {
    return (
        <RagbitsProvider baseUrl="http://localhost:8000">
            <YourApp />
        </RagbitsProvider>
    )
}
```

### Generic API Calls with useRagbitsCall

The `useRagbitsCall` hook provides a React-friendly way to make API calls using the underlying `RagbitsClient`:

```tsx
import { useRagbitsCall } from 'ragbits-api-client-react'

// Define your response types
interface Config {
    model: string
    temperature: number
}

function ConfigComponent() {
    // GET request
    const config = useRagbitsCall<Config>('/api/config')

    // POST request for feedback
    const feedback = useRagbitsCall<{ success: boolean }>('/api/feedback', {
        method: 'POST',
    })

    const handleLoadConfig = async () => {
        try {
            await config.call()
            console.log('Config loaded:', config.data)
        } catch (error) {
            console.error('Failed to load config:', error)
        }
    }

    const handleSendFeedback = async () => {
        try {
            await feedback.call({
                body: {
                    message_id: 'msg-123',
                    feedback: 'positive',
                    payload: { rating: 5 },
                },
            })
            console.log('Feedback sent:', feedback.data)
        } catch (error) {
            console.error('Failed to send feedback:', error)
        }
    }

    return (
        <div>
            <button onClick={handleLoadConfig} disabled={config.isLoading}>
                {config.isLoading ? 'Loading...' : 'Load Config'}
            </button>

            <button onClick={handleSendFeedback} disabled={feedback.isLoading}>
                {feedback.isLoading ? 'Sending...' : 'Send Feedback'}
            </button>

            {config.data && (
                <div>
                    <h3>Config:</h3>
                    <pre>{JSON.stringify(config.data, null, 2)}</pre>
                </div>
            )}

            {config.error && <p>Config Error: {config.error.message}</p>}
            {feedback.error && <p>Feedback Error: {feedback.error.message}</p>}
        </div>
    )
}
```

### Streaming with useRagbitsStream

The `useRagbitsStream` hook provides React state management for streaming responses:

```tsx
import { useRagbitsStream } from 'ragbits-api-client-react'
import type { ChatResponse, ChatRequest } from 'ragbits-api-client-react'

function ChatComponent() {
    const [messages, setMessages] = useState<ChatResponse[]>([])
    const [input, setInput] = useState('')
    const stream = useRagbitsStream<ChatResponse>()

    const handleSendMessage = () => {
        if (!input.trim()) return

        const chatRequest: ChatRequest = {
            message: input,
            history: [],
            context: {},
        }

        stream.stream('/api/chat', chatRequest, {
            onMessage: (response) => {
                setMessages((prev) => [...prev, response])
            },
            onError: (error) => {
                console.error('Stream error:', error)
            },
            onClose: () => {
                console.log('Stream completed')
            },
        })

        setInput('')
    }

    return (
        <div>
            <div>
                {messages.map((msg, index) => (
                    <div key={index}>
                        <strong>{msg.type}:</strong>{' '}
                        {JSON.stringify(msg.content)}
                    </div>
                ))}
            </div>

            <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={stream.isStreaming}
                placeholder="Type your message..."
            />

            <button
                onClick={handleSendMessage}
                disabled={stream.isStreaming || !input.trim()}
            >
                {stream.isStreaming ? 'Streaming...' : 'Send'}
            </button>

            <button onClick={stream.cancel} disabled={!stream.isStreaming}>
                Cancel
            </button>

            {stream.error && <p>Error: {stream.error.message}</p>}
        </div>
    )
}
```

### Using the Core Client Directly

You can also access the underlying `RagbitsClient` instance directly:

```tsx
import { useRagbitsContext } from 'ragbits-api-client-react'

function DirectClientComponent() {
    const { client } = useRagbitsContext()

    const handleDirectCall = async () => {
        // Use the client directly
        const config = await client.getConfig()
        console.log('Config:', config)

        // Or use the generic methods
        const customData = await client.makeRequest('/api/custom-endpoint', {
            method: 'POST',
            body: { custom: 'data' },
        })
    }

    return <button onClick={handleDirectCall}>Use Client Directly</button>
}
```

## Architecture

This package is built on top of `ragbits-api-client` and provides:

- **React-friendly hooks** with proper state management
- **TypeScript support** with full type safety
- **Automatic cleanup** for streams and requests
- **Error handling** with React state
- **Loading states** for better UX

The underlying `RagbitsClient` handles:

- HTTP requests and responses
- Streaming connections
- Error handling at the network level
- URL building and configuration

## API Reference

### RagbitsProvider

Provider component that sets up the `RagbitsClient` instance.

**Props:**

- `baseUrl?: string` - Base URL for the API (default: "http://127.0.0.1:8000")
- `children: ReactNode` - Child components

### useRagbitsCall<T>(endpoint, defaultOptions?)

React hook for making API calls with state management.

**Parameters:**

- `endpoint: string` - API endpoint path
- `defaultOptions?: ApiRequestOptions` - Default request options

**Returns:**

- `data: T | null` - Response data
- `error: Error | null` - Error if request failed
- `isLoading: boolean` - Loading state
- `call: (options?) => Promise<T>` - Function to make the API call
- `reset: () => void` - Reset state to initial values

### useRagbitsStream<T>()

React hook for handling streaming responses with state management.

**Returns:**

- `isStreaming: boolean` - Whether a stream is active
- `error: Error | null` - Stream error
- `stream: (endpoint, data, callbacks) => () => void` - Start streaming
- `cancel: () => void` - Cancel current stream

### useRagbitsContext()

Access the underlying `RagbitsClient` instance.

**Returns:**

- `client: RagbitsClient` - The client instance

### Types

All types from `ragbits-api-client` are re-exported:

```typescript
import type {
    ChatResponse,
    ChatRequest,
    FeedbackRequest,
    StreamCallbacks,
    ClientConfig,
    ApiRequestOptions,
    RagbitsClient,
} from 'ragbits-api-client-react'
```
