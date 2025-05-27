# Ragbits API Client

A TypeScript client for communicating with the Ragbits API. This client provides methods for both regular HTTP requests and server-sent events (streaming) functionality.

## Installation

```bash
npm install ragbits-api-client
```

## Usage

```typescript
import { RagbitsClient, type ChatResponse } from "ragbits-api-client";

// Initialize the client
const client = new RagbitsClient({
  baseUrl: "http://127.0.0.1:8000", // Optional, defaults to http://127.0.0.1:8000
});

// Get API configuration
const config = await client.getConfig();

// Send a chat message with streaming response
const cleanup = client.sendChatMessage(
  {
    message: "Hello!",
    history: [],
    context: {}, // Optional
  },
  {
    onMessage: (data: ChatResponse) => {
      console.log("Received message:", data);
    },
    onError: (error: string) => {
      console.error("Error:", error);
    },
    onClose: () => {
      console.log("Stream closed");
    },
  }
);

// Cancel the stream if needed
cleanup();

// Send feedback
await client.sendFeedback({
  message_id: "message-123",
  feedback: "like",
  payload: { reason: "helpful" },
});
```

## API Reference

### `RagbitsClient`

The main client class for interacting with the Ragbits API.

#### Constructor

```typescript
new RagbitsClient(config?: { baseUrl?: string })
```

- `config.baseUrl` (optional): Base URL for the API. Defaults to 'http://127.0.0.1:8000'

#### Methods

##### `getConfig()`

Get the API configuration.

- Returns: `Promise<Record<string, unknown>>` - API configuration object

##### `sendChatMessage(chatRequest, callbacks)`

Send a chat message and receive streaming responses.

- Parameters:
  - `chatRequest`: ChatRequest
    - `message`: string - User message
    - `history`: Array<{ role: string; content: string; id?: string }> - Chat history
    - `context`: Record<string, unknown> (optional) - Additional context
  - `callbacks`: StreamCallbacks
    - `onMessage`: (data: ChatResponse) => void | Promise<void> - Called when a message chunk is received
    - `onError`: (error: string) => void | Promise<void> - Called when an error occurs
    - `onClose`: () => void | Promise<void> (optional) - Called when the stream closes
- Returns: `() => void` - Cleanup function to cancel the stream

##### `sendFeedback(feedbackData)`

Send feedback for a message.

- Parameters:
  - `feedbackData`: FeedbackRequest
    - `message_id`: string - ID of the message to provide feedback for
    - `feedback`: string - Type of feedback
    - `payload`: Record<string, unknown> | null - Additional feedback data
- Returns: `Promise<Record<string, unknown>>` - Feedback submission response

## Types

### ChatResponse

```typescript
{
  type: "message" | "reference" | "state_update" | "text" | "message_id";
  content: any;
}
```

### ChatRequest

```typescript
{
  message: string;
  history: Array<{
    role: string;
    content: string;
    id?: string;
  }>;
  context?: Record<string, unknown>;
}
```

### FeedbackRequest

```typescript
{
  message_id: string;
  feedback: string;
  payload: Record<string, unknown> | null;
}
```

### StreamCallbacks

```typescript
{
  onMessage: (data: ChatResponse) => void | Promise<void>;
  onError: (error: string) => void | Promise<void>;
  onClose?: () => void | Promise<void>;
}
```
