# @ragbits/api-client

A TypeScript client for communicating with the Ragbits API. This client provides type-safe methods for both regular HTTP requests and server-sent events (streaming) functionality.

## Features

- **Type-safe API calls** - Full TypeScript support with predefined endpoints
- **Streaming support** - Real-time server-sent events with proper error handling
- **Modern JavaScript** - ES modules and CommonJS support
- **Abortable requests** - Cancel ongoing requests and streams
- **Error handling** - Comprehensive error handling with detailed error messages
- **Zero dependencies** - Lightweight with no runtime dependencies

## Installation

```bash
npm install @ragbits/api-client
```

## Quick Start

```typescript
import { RagbitsClient } from '@ragbits/api-client'

// Initialize the client
const client = new RagbitsClient({
    baseUrl: 'http://127.0.0.1:8000', // Optional, defaults to http://127.0.0.1:8000
})

// Get API configuration
const config = await client.makeRequest('/api/config')

// Send a chat message with streaming response
const cleanup = client.makeStreamRequest(
    '/api/chat',
    {
        message: 'Hello!',
        history: [],
        context: {}, // Optional
    },
    {
        onMessage: (data) => {
            console.log('Received message:', data)
        },
        onError: (error) => {
            console.error('Error:', error)
        },
        onClose: () => {
            console.log('Stream closed')
        },
    }
)

// Cancel the stream if needed
cleanup()

// Send feedback
await client.makeRequest('/api/feedback', {
    method: 'POST',
    body: {
        message_id: 'message-123',
        feedback: 'like',
        payload: { reason: 'helpful' },
    },
})
```

## API Reference

### `RagbitsClient`

The main client class for interacting with the Ragbits API.

#### Constructor

```typescript
new RagbitsClient(config?: ClientConfig)
```

**Parameters:**

- `config.baseUrl` (optional): Base URL for the API. Defaults to 'http://127.0.0.1:8000'

**Throws:** `Error` if the base URL is invalid

#### Methods

##### `getBaseUrl(): string`

Get the base URL used by this client.

**Returns:** The configured base URL

##### `async makeRequest<Endpoints, URL>(endpoint, options?): Promise<Result>`

Make a type-safe API request to any endpoint. `endpoint` must be one of the key of `Endpoints` type
that define schema of the available endpoints. All default Ragbits routes are supported out of the box.

**Parameters:**

- `endpoint`: API endpoint path (e.g., '/api/config', '/api/feedback')
- `options` (optional): Request options
    - `method`: HTTP method (defaults to endpoint's predefined method)
    - `body`: Request body (typed based on endpoint)
    - `headers`: Additional headers
    - `signal`: AbortSignal for cancelling the request

**Returns:** Promise with the typed response

**Example:**

```typescript
// GET request
const config = await client.makeRequest('/api/config')

// POST request
const feedback = await client.makeRequest('/api/feedback', {
    method: 'POST',
    body: {
        message_id: 'msg-123',
        feedback: 'like',
        payload: { rating: 5 },
    },
})

// Custom endpoints
type MyEndpoints = {
    '/api/my-endpoint': {
        method: 'GET'
        request: never
        response: string
    }
}

// or
type ExtendedEndpoints = BaseApiEndpoints & {
    '/api/my-endpoint': {
        method: 'GET'
        request: never
        response: string
    }
}

// In case of usage of custom Endpoints, we have to specify the URL as generic parameter
const myResponse = await client.makeRequest<MyEndpoints, '/api/my-endpoint'>(
    '/api/my-endpoint'
)
```

##### `makeStreamRequest<Endpoints, URL>(endpoint, data, callbacks, signal?): () => void`

Make a type-safe streaming request to any streaming endpoints. `endpoint` must be one of the key of `Endpoints` type
that define schema of the available endpoints. All default Ragbits routes are supported out of the box.

**Parameters:**

- `endpoint`: Streaming endpoint path (e.g., '/api/chat')
- `data`: Request data (typed based on endpoint)
- `callbacks`: Stream callbacks
    - `onMessage`: Called when a message chunk is received
    - `onError`: Called when an error occurs
    - `onClose`: Called when the stream closes (optional)
- `signal` (optional): AbortSignal for cancelling the stream

**Returns:** Cleanup function to cancel the stream

**Example:**

```typescript
const cleanup = client.makeStreamRequest(
    '/api/chat',
    {
        message: 'Tell me about AI',
        history: [
            { role: 'user', content: 'Hello', id: 'msg-1' },
            { role: 'assistant', content: 'Hi there!', id: 'msg-2' },
        ],
        context: { user_id: 'user-123' },
    },
    {
        onMessage: (data) => {
            switch (data.type) {
                case 'text':
                    console.log('Text:', data.content)
                    break
                case 'reference':
                    console.log('Reference:', data.content.title)
                    break
                case 'message_id':
                    console.log('Message ID:', data.content)
                    break
            }
        },
        onError: (error) => {
            console.error('Stream error:', error)
        },
        onClose: () => {
            console.log('Stream completed')
        },
    }
)

// Cancel stream
cleanup()

// Custom endpoints
type MyEndpoints = {
    '/api/my-endpoint': {
        method: 'GET'
        request: never
        response: string
    }
}

// In case of usage of custom Endpoints, we have to specify the URL as generic parameter
const cleanup = client.makeStreamRequest<MyEndpoints, '/api/my-endpoint'>(
    '/api/my-endpoint',
    ...
)
```

## Error Handling

The client provides comprehensive error handling:

```typescript
try {
    const config = await client.makeRequest('/api/config')
} catch (error) {
    if (error instanceof Error) {
        console.error('API Error:', error.message)
    }
}
```

Common error scenarios:

- **Network errors** - Connection failures, timeouts
- **HTTP errors** - 4xx/5xx status codes
- **Invalid URLs** - Malformed base URL
- **Stream errors** - Connection drops, parsing errors

## Aborting Requests

Both regular requests and streams can be aborted:

```typescript
// Abort regular request
const controller = new AbortController()
const request = client.makeRequest('/api/config', {
    signal: controller.signal,
})
controller.abort() // Cancels the request

// Abort stream
const cleanup = client.makeStreamRequest(
    '/api/chat',
    data,
    callbacks,
    controller.signal
)
controller.abort() // Cancels the stream
cleanup() // Also cancels the stream
```

## Browser Support

This package supports all modern browsers with fetch API support:

- Chrome 42+
- Firefox 39+
- Safari 10.1+
- Edge 14+

## Node.js Support

For Node.js environments, you'll need:

- Node.js 18+

## License

MIT
