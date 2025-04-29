# How-To: Set up an API Server with UI for a chatbot in Ragbits

This guide shows you how to set up a Ragbits API server with a web UI for your chatbot application.

## Step 1: Create a Chat Implementation

First, create a chat implementation by subclassing `ChatInterface`. Here's a minimal example:

```python
from collections.abc import AsyncGenerator

from ragbits.api.interface import ChatInterface
from ragbits.api.interface.types import ChatResponse, Message
from ragbits.core.llms import LiteLLM

class MyChat(ChatInterface):
    def __init__(self) -> None:
        self.llm = LiteLLM(model_name="gpt-4o-mini")

    async def chat(
        self,
        message: str,
        history: list[Message] | None = None,
        context: dict | None = None,
    ) -> AsyncGenerator[ChatResponse, None]:
        async for chunk in self.llm.generate_streaming([*history, {"role": "user", "content": message}]):
            yield self.create_text_response(chunk)
```

Save this to a file, for example `chat.py`.

## Step 2: Add Feedback Configuration (Optional)

You can enable user feedback by adding a feedback configuration:

```python
from ragbits.api.interface.forms import FeedbackConfig, FeedbackForm, FormField

# Add this to your ChatInterface class
feedback_config = FeedbackConfig(
    like_enabled=True,
    like_form=FeedbackForm(
        title="Like Form",
        fields=[
            FormField(name="like_reason", type="text", required=True, label="Why do you like this?"),
        ],
    ),
    dislike_enabled=True,
    dislike_form=FeedbackForm(
        title="Dislike Form",
        fields=[
            FormField(
                name="issue_type",
                type="select",
                required=True,
                label="What was the issue?",
                options=["Incorrect information", "Not helpful", "Unclear", "Other"],
            ),
            FormField(name="feedback", type="text", required=True, label="Please provide more details"),
        ],
    ),
)
```

## Step 3: Add Reference Support (Optional)

To include references in your responses:

```python
# Inside your chat method
yield self.create_reference(
    title="Example Reference",
    content="This is a reference document that might be relevant to your query.",
    url="https://example.com/reference1",
)
```

## Step 4: Launch the API Server

You can start the API server using the Ragbits CLI:

```bash
ragbits api run path.to.your.module:MyChat
```

Or programmatically:

```python
from ragbits.api._main import RagbitsAPI

api = RagbitsAPI(
    chat_interface="path.to.your.module:MyChat",
    cors_origins=["http://localhost:3000"],  # Optional: Add CORS origins if needed
    ui_build_dir=None,  # Optional: Path to custom UI build
)
api.run(host="127.0.0.1", port=8000)
```

## Step 5: Access the Web UI

Open your browser and navigate to:

```
http://127.0.0.1:8000
```

You'll see the chat interface where you can interact with your chatbot.

## Customization Options

### Custom UI

To use a custom UI, specify the `ui_build_dir` parameter when creating the `RagbitsAPI` instance:

```python
api = RagbitsAPI(
    chat_interface="path.to.your.module:MyChat",
    ui_build_dir="/path/to/your/ui/build",
)
api.run(host="127.0.0.1", port=8000)
```

### CORS Configuration

To allow cross-origin requests, specify the allowed origins:

```python
api = RagbitsAPI(
    chat_interface="path.to.your.module:MyChat",
    cors_origins=["http://localhost:3000", "https://your-domain.com"],
)
api.run(host="127.0.0.1", port=8000)
```

## API Endpoints

The API server exposes the following endpoints:

- `GET /`: Serves the web UI
- `POST /api/chat`: Accepts chat messages and returns streaming responses
- `GET /api/config`: Returns UI configuration including feedback forms

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

## Complete Example

Here's a complete example of a chat implementation:

```python
from collections.abc import AsyncGenerator

from ragbits.api.interface import ChatInterface
from ragbits.api.interface.forms import FeedbackConfig, FeedbackForm, FormField
from ragbits.api.interface.types import ChatResponse, Message
from ragbits.core.llms import LiteLLM

class MyChat(ChatInterface):
    """A simple example implementation of the ChatInterface."""

    feedback_config = FeedbackConfig(
        like_enabled=True,
        like_form=FeedbackForm(
            title="Like Form",
            fields=[
                FormField(name="like_reason", type="text", required=True, label="Why do you like this?"),
            ],
        ),
        dislike_enabled=True,
        dislike_form=FeedbackForm(
            title="Dislike Form",
            fields=[
                FormField(
                    name="issue_type",
                    type="select",
                    required=True,
                    label="What was the issue?",
                    options=["Incorrect information", "Not helpful", "Unclear", "Other"],
                ),
                FormField(name="feedback", type="text", required=True, label="Please provide more details"),
            ],
        ),
    )

    def __init__(self) -> None:
        self.llm = LiteLLM(model_name="gpt-4o-mini")

    async def chat(
        self,
        message: str,
        history: list[Message] | None = None,
        context: dict | None = None,
    ) -> AsyncGenerator[ChatResponse, None]:
        # Add reference documents if needed
        yield self.create_reference(
            title="Example Reference",
            content="This is an example reference document that might be relevant to your query.",
            url="https://example.com/reference1",
        )

        # Stream the response from the LLM
        async for chunk in self.llm.generate_streaming([*history, {"role": "user", "content": message}]):
            yield self.create_text_response(chunk)
```
