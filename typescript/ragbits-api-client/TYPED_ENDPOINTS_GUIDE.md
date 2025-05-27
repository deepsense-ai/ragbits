# Typed Endpoints Guide

This guide explains the strongly typed API client system with separated endpoint types.

## Overview

The API client now separates endpoints into two categories:

1. **Regular API Endpoints** - Traditional request/response patterns
2. **Streaming Endpoints** - Real-time streaming patterns

## Current Endpoints

### Regular API Endpoints

- `/api/config` - GET - Configuration retrieval
- `/api/feedback` - POST - Feedback submission

### Streaming Endpoints

- `/api/chat` - POST - Real-time chat streaming

## Usage Examples

### Regular API Calls

```typescript
const client = new RagbitsClient();

// Strongly typed GET request
const config = await client.makeRequest("/api/config");

// Strongly typed POST request
const feedback = await client.makeRequest("/api/feedback", {
  method: "POST",
  body: { message_id: "123", feedback: "positive", payload: null },
});
```

### Streaming API Calls

```typescript
// Strongly typed streaming
const cancel = client.makeStreamRequest(
  "/api/chat",
  {
    message: "Hello!",
    history: [],
    context: {},
  },
  {
    onMessage: (response) => console.log(response),
    onError: (error) => console.error(error),
  }
);
```

## Key Benefits

- **Consistent API** - All endpoints use the same `makeRequest`/`makeStreamRequest` pattern
- **Full Type Safety** - TypeScript validates endpoints, methods, requests, and responses
- **Extensible** - Works seamlessly with custom endpoints
- **IntelliSense Support** - Full autocomplete and documentation

## Extending Endpoints

```typescript
declare module "ragbits-api-client" {
  interface ApiEndpoints {
    "/api/users": {
      method: "GET";
      request: never;
      response: { users: User[] };
    };
  }

  interface StreamingEndpoints {
    "/api/live-updates": {
      method: "POST";
      request: { subscriptions: string[] };
      stream: { type: string; data: object };
    };
  }
}
```

This provides full type safety and IntelliSense support for all your API interactions.
