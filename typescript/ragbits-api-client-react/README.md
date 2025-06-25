# @ragbits/api-client-react

React hooks for the Ragbits API client. This package provides React-friendly hooks built on top of the core `@ragbits/api-client` package with full TypeScript support and automatic state management.

## Features

- **React hooks** - Type-safe hooks for API calls and streaming
- **Automatic state management** - Loading states, error handling, and data caching
- **Request cancellation** - Built-in abort functionality for ongoing requests
- **Streaming support** - Real-time streaming with React state integration
- **TypeScript support** - Full type safety with predefined endpoints
- **Context provider** - Easy setup with React Context

## Installation

```bash
npm install @ragbits/api-client-react
```

**Note:** This package depends on `@ragbits/api-client` which will be installed automatically.

## Quick Start

### 1. Setup Provider

First, wrap your app with the `RagbitsProvider`:

```tsx
import { RagbitsProvider } from '@ragbits/api-client-react'

function App() {
    return (
        <RagbitsProvider baseUrl="http://localhost:8000">
            <YourApp />
        </RagbitsProvider>
    )
}
```

### 2. Hooks Usage Examples

#### API Call Example

```tsx
import { useRagbitsCall } from '@ragbits/api-client-react'

function ConfigComponent() {
    const config = useRagbitsCall('/api/config')

    const handleLoadConfig = async () => {
        try {
            await config.call()
            console.log('Config loaded:', config.data)
        } catch (error) {
            console.error('Failed to load config:', error)
        }
    }

    return (
        <div>
            <button onClick={handleLoadConfig} disabled={config.isLoading}>
                {config.isLoading
                    ? 'Loading...'
                    : config.data
                      ? 'Reload Config'
                      : 'Load Config'}
            </button>

            {config.data && (
                <div>
                    <h3>Config loaded successfully</h3>
                </div>
            )}

            {config.error && <p>Error: {config.error.message}</p>}
        </div>
    )
}
```

#### Streaming Example

```tsx
import { useRagbitsStream } from '@ragbits/api-client-react'

function ChatComponent() {
    const chatStream = useRagbitsStream('/api/chat')

    const handleSendMessage = () => {
        const chatRequest = {
            message: 'Hello!',
            history: [],
            context: {},
        }

        chatStream.stream(chatRequest, {
            onMessage: (chunk) => {
                console.log('chunk:', chunk)
            },
            onError: (error) => {
                console.error('Stream error:', error)
            },
            onClose: () => {
                console.log('Stream completed')
            },
        })
    }

    return (
        <div>
            <button
                onClick={handleSendMessage}
                disabled={chatStream.isStreaming}
            >
                {chatStream.isStreaming ? 'Streaming...' : 'Send Message'}
            </button>

            <button
                onClick={chatStream.cancel}
                disabled={!chatStream.isStreaming}
            >
                Cancel
            </button>

            {chatStream.error && <p>Error: {chatStream.error.message}</p>}
        </div>
    )
}
```

## API Reference

### `RagbitsProvider`

Provider component that sets up the `RagbitsClient` instance and provides it to the React context.

**Props:**

```typescript
interface RagbitsProviderProps {
    baseUrl?: string // Base URL for the API (default: "http://127.0.0.1:8000")
    children: ReactNode
}
```

### `useRagbitsCall<T>(endpoint, defaultOptions?)`

React hook for making type-safe API calls with automatic state management.

**Parameters:**

- `endpoint`: Predefined API endpoint path (e.g., '/api/config', '/api/feedback')
- `defaultOptions` (optional): Default request options

**Returns:**

```typescript
interface RagbitsCallResult<T, E = Error> {
    data: T | null // Response data
    error: E | null // Error if request failed
    isLoading: boolean // Loading state
    call: (options?) => Promise<T> // Function to make the API call
    reset: () => void // Reset state to initial values
    abort: () => void // Abort current request
}
```

### `useRagbitsStream<T>(endpoint)`

React hook for handling streaming responses with automatic state management.

**Parameters:**

- `endpoint`: Predefined streaming endpoint path (e.g., '/api/chat')

**Returns:**

```typescript
interface RagbitsStreamResult<E = Error> {
    isStreaming: boolean // Whether a stream is active
    error: E | null // Stream error
    stream: (data, callbacks) => () => void // Start streaming
    cancel: () => void // Cancel current stream
}
```

### `useRagbitsContext()`

Access the underlying `RagbitsClient` instance directly.

**Returns:**

```typescript
interface RagbitsContextValue {
    client: RagbitsClient
}
```

## Types

All types from `@ragbits/api-client` are re-exported:

```typescript
import type {
    // Core types
    RagbitsClient,
    ClientConfig,

    // Request/Response types
    ChatRequest,
    FeedbackRequest,
    ConfigResponse,
    FeedbackResponse,

    // Message types
    Message,
    MessageRole,
    TypedChatResponse,
    ChatResponseType,

    // Feedback types
    FeedbackType,

    // Stream types
    StreamCallbacks,

    // Endpoint types
    ApiEndpointPath,
    StreamingEndpointPath,
    ApiEndpointResponse,
    StreamingEndpointStream,
    TypedApiRequestOptions,
} from '@ragbits/api-client-react'
```

## Browser Support

This package supports all modern browsers with React 16.8+ (for hooks):

- Chrome 42+
- Firefox 39+
- Safari 10.1+
- Edge 14+

## Node.js Support

For Node.js environments, you'll need:

- Node.js 18+

## License

MIT
