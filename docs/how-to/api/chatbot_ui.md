# Setting up an API Server with UI for a Chatbot

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
```

### CORS Configuration

To allow cross-origin requests, specify the allowed origins:

```python
api = RagbitsAPI(
    chat_interface="path.to.your.module:MyChat",
    cors_origins=["http://localhost:3000", "https://your-domain.com"],
)
```

## API Endpoints

The API server exposes the following endpoints:

- `GET /`: Serves the web UI
- `POST /api/chat`: Accepts chat messages and returns streaming responses
- `GET /api/config`: Returns UI configuration including feedback forms

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
