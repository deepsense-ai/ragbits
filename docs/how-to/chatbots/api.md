# How-To: Set up an API Server with UI for a chatbot in Ragbits

This guide shows you how to set up a Ragbits API server with a web UI for your chatbot application, covering all response types, customization options, and advanced features.

## Quick Start

### 1. Create a Basic Chat Implementation

First, create a chat implementation by subclassing `ChatInterface`. Here's a minimal example:

```python
from collections.abc import AsyncGenerator

from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import ChatResponse
from ragbits.core.prompt import ChatFormat
from ragbits.core.llms import LiteLLM

class MyChat(ChatInterface):
    def __init__(self) -> None:
        self.llm = LiteLLM(model_name="gpt-4o-mini")

    async def chat(
        self,
        message: str,
        history: ChatFormat,
        context: ChatContext,
    ) -> AsyncGenerator[ChatResponse, None]:
        async for chunk in self.llm.generate_streaming([*history, {"role": "user", "content": message}]):
            yield self.create_text_response(chunk)
```

Save this to a file, for example `chat.py`.

### 2. Start the User Interface

Launch the API server with the built-in web UI using the Ragbits CLI:

```bash
ragbits api run path.to.your.module:MyChat
```

> **Note**: `path.to.your.module` should be the dotted Python _module path_ **without** the `.py` extension.

The server will start on **port 8000** by default. Open your browser and navigate to:

```
http://127.0.0.1:8000
```

You'll see the chat interface where you can interact with your chatbot immediately.

## Response Types

Ragbits Chat supports multiple response types that can be yielded from your `chat` method to create rich, interactive experiences.

### Text Responses

Text responses are the primary way to stream content to users. Use `create_text_response()` to yield text chunks:

```python
async def chat(self, message: str, history: ChatFormat, context: ChatContext) -> AsyncGenerator[ChatResponse, None]:
    # Stream response from LLM
    async for chunk in self.llm.generate_streaming([*history, {"role": "user", "content": message}]):
        yield self.create_text_response(chunk)
```

### References

References allow you to cite sources, documents, or external links that support your response:

```python
async def chat(self, message: str, history: ChatFormat, context: ChatContext) -> AsyncGenerator[ChatResponse, None]:
    # Add a reference
    yield self.create_reference(
        title="Example Reference",
        content="This is an example reference document that might be relevant to your query.",
        url="https://example.com/reference1",
    )
```

### Images

You can include images in your responses using `create_image_response()`:

```python
import uuid

async def chat(self, message: str, history: ChatFormat, context: ChatContext) -> AsyncGenerator[ChatResponse, None]:
    # Add an image to the response
    yield self.create_image_response(
        str(uuid.uuid4()),  # Unique identifier for the image
        "https://example.com/image.jpg"  # Image URL
    )
```

### Follow-up Messages

Provide suggested follow-up questions to guide the conversation:

```python
async def chat(self, message: str, history: ChatFormat, context: ChatContext) -> AsyncGenerator[ChatResponse, None]:
    # Main response...
    async for chunk in self.llm.generate_streaming([*history, {"role": "user", "content": message}]):
        yield self.create_text_response(chunk)

    # Add follow-up suggestions
    yield self.create_followup_messages([
        "Tell me more about this topic",
        "Can you provide another example?",
        "How does this relate to X?"
    ])
```

> **Note**: Follow-up messages will be displayed as buttons which will be sent to the server as a message after the user clicks on the button.

### Live Updates

Live updates show real-time progress for long-running operations (like web searches, API calls, or data processing):

```python
import asyncio
from ragbits.chat.interface.types import LiveUpdateType

async def chat(self, message: str, history: ChatFormat, context: ChatContext) -> AsyncGenerator[ChatResponse, None]:
    # Start a live update
    yield self.create_live_update(
        "search_task",  # Unique task ID
        LiveUpdateType.START,
        "Searching the web for information..."
    )

    # Simulate some work
    await asyncio.sleep(2)

    # Update the live task
    yield self.create_live_update(
        "search_task",
        LiveUpdateType.FINISH,
        "Web search completed",
        "Found 5 relevant results."  # Optional description
    )

    # You can have multiple concurrent live updates
    yield self.create_live_update(
        "analysis_task",
        LiveUpdateType.FINISH,
        "Analysis completed",
        "Processed 3 documents."
    )

    # Continue with text response...
    async for chunk in self.llm.generate_streaming([*history, {"role": "user", "content": message}]):
        yield self.create_text_response(chunk)
```

## Handling File Uploads

Ragbits Chat supports file uploads, allowing users to send files to your chatbot. To enable this feature, implement the `upload_handler` method in your `ChatInterface` subclass.

### Enable File Uploads

Define an async `upload_handler` method that accepts a `fastapi.UploadFile` object:

```python
from collections.abc import AsyncGenerator

from fastapi import UploadFile

from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import ChatContext, ChatResponse
from ragbits.core.prompt import ChatFormat


class MyChat(ChatInterface):
    async def upload_handler(self, file: UploadFile) -> None:
        """
        Handle file uploads.

        Args:
            file: The uploaded file (FastAPI UploadFile)
        """
        # Read the file content
        content = await file.read()
        filename = file.filename

        # Process the file (e.g., ingest into vector store, save to disk)
        print(f"Received file: {filename}, size: {len(content)} bytes")

    async def chat(
        self,
        message: str,
        history: ChatFormat,
        context: ChatContext,
    ) -> AsyncGenerator[ChatResponse, None]:
        yield self.create_text_response(f"You said: {message}")
```

When this method is implemented, the chat interface will automatically show an attachment icon in the input bar.

> **Note**: The upload handler processes the file but does not directly return a response to the chat stream. The frontend receives a success status via the `/api/upload` endpoint. If you want to acknowledge the upload in the chat, the user typically sends a follow-up message, or you can store the uploaded file reference in state for later use.

## State Management

Ragbits Chat provides secure state management to maintain conversation context across requests. State data is automatically signed using HMAC to prevent tampering.

### Storing State

Use `create_state_update()` to store state information that persists across conversation turns:

```python
from ragbits.chat.interface.types import ChatContext
from ragbits.core.prompt import ChatFormat

async def chat(
    self,
    message: str,
    history: ChatFormat,
    context: ChatContext
) -> AsyncGenerator[ChatResponse, None]:
    # Access existing state from context
    current_state = context.state if context else {}

    # Update state with new information
    new_state = {
        **current_state,
        "user_preference": "example_value",
        "conversation_count": current_state.get("conversation_count", 0) + 1,
        "last_topic": "extracted from current message"
    }

    # Store the updated state
    yield self.create_state_update(new_state)
```

### Security Considerations

- State data is automatically signed with HMAC-SHA256 to prevent client-side tampering
- The secret key is obtained from the `RAGBITS_SECRET_KEY` environment variable
- If no environment variable is set, a random key is generated (with a warning)
- For production, always set `RAGBITS_SECRET_KEY` to a strong, unique value
- State signatures are verified on each request - tampering results in a 400 error

## User Interface Configuration

### Configure User Forms

Ragbits Chat supports two types of user forms: feedback forms and user settings forms.

#### Feedback Forms

Configure feedback forms to collect user ratings and comments:

```python
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from ragbits.chat.interface.forms import FeedbackConfig

class LikeFormExample(BaseModel):
    """Form shown when user likes a response."""
    model_config = ConfigDict(
        title="Like Form",
        json_schema_serialization_defaults_required=True,
    )

    like_reason: str = Field(
        description="Why do you like this response?",
        min_length=1,
    )

class DislikeFormExample(BaseModel):
    """Form shown when user dislikes a response."""
    model_config = ConfigDict(
        title="Dislike Form",
        json_schema_serialization_defaults_required=True
    )

    issue_type: Literal["Incorrect information", "Not helpful", "Unclear", "Other"] = Field(
        description="What was the issue?"
    )
    feedback: str = Field(
        description="Please provide more details",
        min_length=1
    )

class MyChat(ChatInterface):
    feedback_config = FeedbackConfig(
        like_enabled=True,
        like_form=LikeFormExample,
        dislike_enabled=True,
        dislike_form=DislikeFormExample,
    )

    # ... rest of your implementation
```

#### User Settings Forms

Configure user settings forms to collect user preferences:

```python
from ragbits.chat.interface.forms import UserSettings

class UserSettingsFormExample(BaseModel):
    """Form for user preferences and settings."""
    model_config = ConfigDict(
        title="User Settings",
        json_schema_serialization_defaults_required=True
    )

    language: Literal["English", "Spanish", "French", "German"] = Field(
        description="Preferred language",
        default="English"
    )

    response_style: Literal["Concise", "Detailed", "Technical"] = Field(
        description="How would you like responses formatted?",
        default="Detailed"
    )

class MyChat(ChatInterface):
    user_settings = UserSettings(form=UserSettingsFormExample)

    # ... rest of your implementation
```

### Customize UI Appearance

Configure the chat interface appearance with custom icons, headers, and messages:

```python
from ragbits.chat.interface.ui_customization import (
    UICustomization,
    HeaderCustomization,
    PageMetaCustomization
)

class MyChat(ChatInterface):
    ui_customization = UICustomization(
        # Header customization
        header=HeaderCustomization(
            title="My AI Assistant",
            subtitle="Powered by Ragbits",
            logo="🤖"
        ),

        # Welcome message shown when chat starts
        welcome_message=(
            "Hello! I'm your AI assistant.\n\n"
            "How can I help you today? You can ask me **anything**! "
            "I can provide information, answer questions, and assist with various tasks."
        ),

        # Page metadata
        meta=PageMetaCustomization(
            favicon="🤖",
            page_title="My AI Assistant"
        )
    )

    # ... rest of your implementation
```

### Enable Conversation History

To enable conversation history persistence across sessions, set the `conversation_history` attribute:

```python
class MyChat(ChatInterface):
    conversation_history = True  # Enable conversation history

    # ... rest of your implementation
```

When enabled, the chat interface will automatically maintain conversation history and show it in side panel.

## API Endpoints

The API server exposes the following endpoints:

- `GET /`: Serves the web UI
- `GET /api/config`: Returns UI configuration including feedback forms
- `POST /api/chat`: Accepts chat messages and returns streaming responses
- `POST /api/feedback`: Accepts feedback from the user
- `POST /api/upload`: Accepts file uploads (only available when `upload_handler` is implemented)

## Server Configuration

### Launch the API Server

You can start the API server using the Ragbits CLI:

```bash
ragbits api run path.to.your.module:MyChat
```

> **Note**: `path.to.your.module` should be the dotted Python _module path_ **without** the `.py` extension.

### Custom UI

To use a custom UI build, use the `--ui-build-dir` option:

```bash
ragbits api run path.to.your.module:MyChat --ui-build-dir /path/to/your/ui/build
```

### CORS Configuration

To allow cross-origin requests, use the `--cors-origin` option (can be specified multiple times):

```bash
ragbits api run path.to.your.module:MyChat --cors-origin http://localhost:3000 --cors-origin https://your-domain.com
```

### Custom Host and Port

To run on a different host or port:

```bash
ragbits api run path.to.your.module:MyChat --host 0.0.0.0 --port 9000
```

### Enable Debug Mode

To enable debug mode for detailed logging and error information, use the `--debug` flag. It will enable button in UI to toggle debug side panel which will show you all the internal state of the chat:

```bash
ragbits api run path.to.your.module:MyChat --debug
```

## Complete Example

Here's a comprehensive example demonstrating all features of a Ragbits Chat implementation:

```python
import asyncio
import uuid
from collections.abc import AsyncGenerator
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.forms import FeedbackConfig, UserSettings
from ragbits.chat.interface.types import ChatContext, ChatResponse, LiveUpdateType
from ragbits.core.prompt import ChatFormat
from ragbits.chat.interface.ui_customization import HeaderCustomization, PageMetaCustomization, UICustomization
from ragbits.core.llms import LiteLLM


class LikeFormExample(BaseModel):
    """Form shown when user likes a response."""
    model_config = ConfigDict(
        title="Like Form",
        json_schema_serialization_defaults_required=True,
    )

    like_reason: str = Field(
        description="Why do you like this response?",
        min_length=1,
    )


class DislikeFormExample(BaseModel):
    """Form shown when user dislikes a response."""
    model_config = ConfigDict(
        title="Dislike Form",
        json_schema_serialization_defaults_required=True
    )

    issue_type: Literal["Incorrect information", "Not helpful", "Unclear", "Other"] = Field(
        description="What was the issue?"
    )
    feedback: str = Field(
        description="Please provide more details",
        min_length=1
    )


class UserSettingsFormExample(BaseModel):
    """Form for user preferences and settings."""
    model_config = ConfigDict(
        title="User Settings",
        json_schema_serialization_defaults_required=True
    )

    language: Literal["English", "Spanish", "French"] = Field(
        description="Preferred language",
        default="English"
    )

    response_style: Literal["Concise", "Detailed", "Technical"] = Field(
        description="Response style preference",
        default="Detailed"
    )


class MyChat(ChatInterface):
    """A comprehensive example implementation of the ChatInterface with all features."""

    # Configure feedback forms
    feedback_config = FeedbackConfig(
        like_enabled=True,
        like_form=LikeFormExample,
        dislike_enabled=True,
        dislike_form=DislikeFormExample,
    )

    # Configure user settings
    user_settings = UserSettings(form=UserSettingsFormExample)

    # Customize UI appearance
    ui_customization = UICustomization(
        header=HeaderCustomization(
            title="My AI Assistant",
            subtitle="Powered by Ragbits",
            logo="🤖"
        ),
        welcome_message=(
            "Hello! I'm your AI assistant.\n\n"
            "How can I help you today? You can ask me **anything**! "
            "I can provide information, answer questions, and assist with various tasks."
        ),
        meta=PageMetaCustomization(
            favicon="🤖",
            page_title="My AI Assistant"
        ),
    )

    # Enable conversation history
    conversation_history = True

    def __init__(self) -> None:
        self.llm = LiteLLM(model_name="gpt-4o-mini")

    async def chat(
        self,
        message: str,
        history: ChatFormat,
        context: ChatContext,
    ) -> AsyncGenerator[ChatResponse, None]:
        """
        Comprehensive chat implementation demonstrating all response types.

        Args:
            message: The current user message
            history: Optional list of previous messages in the conversation
            context: Optional context including state and user settings

        Yields:
            ChatResponse objects with various content types
        """
        # Access and update state
        current_state = context.state if context else {}
        conversation_count = current_state.get("conversation_count", 0) + 1

        updated_state = {
            **current_state,
            "conversation_count": conversation_count,
            "last_message_length": len(message),
            "user_preference": "example_value"
        }

        yield self.create_state_update(updated_state)

        # Add reference documents
        yield self.create_reference(
            title="Example Reference Document",
            content="This is an example reference that might be relevant to your query.",
            url="https://example.com/reference1",
        )

        # Add an example image
        yield self.create_image_response(
            str(uuid.uuid4()),
            "https://picsum.photos/400/300"
        )

        # Demonstrate live updates for long-running operations
        example_live_updates = [
            self.create_live_update(
                "search_task",
                LiveUpdateType.START,
                "Searching for information..."
            ),
            self.create_live_update(
                "search_task",
                LiveUpdateType.FINISH,
                "Search completed",
                f"Found {conversation_count * 3} relevant results."
            ),
            self.create_live_update(
                "analysis_task",
                LiveUpdateType.FINISH,
                "Analysis completed",
                "Processed and analyzed the search results."
            ),
        ]

        for live_update in example_live_updates:
            yield live_update
            await asyncio.sleep(1)  # Simulate processing time

        # Personalize response based on conversation count
        if conversation_count == 1:
            intro_text = "Welcome! This is our first conversation. "
        elif conversation_count > 5:
            intro_text = f"We've been chatting quite a bit ({conversation_count} messages)! "
        else:
            intro_text = ""

        # Stream the main response from the LLM
        full_prompt = [
            *history,
            {"role": "user", "content": f"{intro_text}{message}"}
        ]

        async for chunk in self.llm.generate_streaming(full_prompt):
            yield self.create_text_response(chunk)

        # Add follow-up suggestions
        yield self.create_followup_messages([
            "Tell me more about this topic",
            "Can you provide another example?",
            "How does this relate to other concepts?"
        ])


```

Save this as `my_chat.py` and run it with:

```bash
ragbits api run my_chat:MyChat --debug
```

Then open http://127.0.0.1:8000 in your browser to see your fully-featured chat interface!
