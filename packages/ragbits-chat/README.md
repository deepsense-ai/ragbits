# Ragbits Conversation

Ragbits Conversation is a Python package that provides tools for building conversational AI applications. It is currently in the early stages of development.

## State Management and Security

The Ragbits Chat API implements secure state management through HMAC signature verification. State data is signed using a secret key to prevent tampering.

### How State Verification Works

1. When the chat interface creates a state update, it automatically signs the state with an HMAC-SHA256 signature.
2. Both the state and its signature are sent to the client as a `state_update` event.
3. When the client sends a request with state data back to the server, it must include both the state and the signature.
4. The API verifies the signature to ensure the state hasn't been tampered with.
5. If verification fails, the API returns a 400 Bad Request error.

### Client-Side Implementation

When receiving a state update from the API:

```javascript
// Example client-side handling of state updates
eventSource.addEventListener('message', (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'state_update') {
    // Store both state and signature
    localStorage.setItem('chatState', JSON.stringify(data.content.state));
    localStorage.setItem('stateSignature', data.content.signature);
  }
});
```

When sending a request that includes state:

```javascript
// Example client-side sending of state with signature
const sendMessage = async (message) => {
  const state = JSON.parse(localStorage.getItem('chatState') || '{}');
  const signature = localStorage.getItem('stateSignature');
  
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      history: messageHistory,
      context: {
        state,
        signature
      }
    })
  });
  
  // Handle response...
};
```

### Security Considerations

- The secret key is obtained from the `RAGBITS_SECRET_KEY` environment variable.
- If the environment variable is not set, a random key is generated automatically with a warning. This key will be regenerated on restart, breaking any existing signatures.
- For production use, you should set the `RAGBITS_SECRET_KEY` environment variable to a strong, unique key.
- Do not expose the secret key to clients.
- The state signature protects against client-side tampering but doesn't encrypt the state data.