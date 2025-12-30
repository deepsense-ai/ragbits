# Tutorial: Building Tool-Powered Chat Interfaces with Agents

Let's build a **sophisticated chatbot interface** with **Ragbits Chat and Agents**. We'll create an intelligent chat system that uses AI agents with real tools to provide web search results, generate images, and deliver live updates during processing.

**What you'll learn:**

- How to create an agent-powered chat interface with real tools (web search, image generation)
- How to implement live updates that show tool execution progress
- How to extract and display web search references automatically
- How to handle image generation with base64 encoding and chunking
- How to build authentication-enabled chat interfaces
- How to configure user settings and feedback forms
- How to customize the chat UI with branding and welcome messages
- How to debug and optimize tool-powered chat systems
- How to build production-ready intelligent assistants with real capabilities

Install the latest Ragbits via `pip install -U ragbits` and follow along.

## Configuring the environment

During development, we will use OpenAI's `gpt-4o-2024-08-06` model with tools. To authenticate, Ragbits will look into your `OPENAI_API_KEY`. You can easily swap this out for [other providers](../how-to/llms/use_llms.md) or [local models](../how-to/llms/use_local_llms.md).

!!! tip "Recommended: Set up OpenTelemetry tracing to understand what's happening under the hood."
OpenTelemetry is an LLMOps tool that natively integrates with Ragbits and offers explainability and experiment tracking. In this tutorial, you can use OpenTelemetry to visualize prompts and tool calls as traces. Check the full setup guide [here](../how-to/audit/use_tracing.md/#using-opentelemetry-tracer).

## Step 1: Basic Agent Setup with Prompt

Let's start by creating the foundation - an agent with a specialized prompt for mountain hiking assistance. This establishes the core AI behavior and domain expertise.

Create a file called `mountain_chat.py` and add the basic structure:

```python
import base64
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ragbits.agents import Agent, ToolCallResult
from ragbits.agents.tools.openai import get_image_generation_tool, get_web_search_tool
from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import ChatContext, ChatResponse, LiveUpdateType, Message
from ragbits.core.llms import LiteLLM, ToolCall
from ragbits.core.prompt import Prompt

# Define the agent's input format
class GeneralAssistantPromptInput(BaseModel):
    """Input format for the General Assistant Prompt."""
    query: str
    language: str

# Create the agent prompt with domain expertise
class GeneralAssistantPrompt(Prompt[GeneralAssistantPromptInput]):
    """Prompt that responds to user queries using appropriate tools."""

    system_prompt = """
    You are a helpful assistant that is expert in mountain hiking and answers user questions.
    You have access to the following tools: web search and image generation.

    Guidelines:
    1. Use the web search tool when the user asks for factual information, research, or current events.
    2. Use the image generation tool when the user asks to create, generate, draw, or produce images.
    3. The image generation tool generates images in 512x512 resolution.
    4. Return the image as a base64 encoded string in the response.
    5. Always select the most appropriate tool based on the user's request.
    6. If the user asks explicitly for a picture, use only the image generation tool.
    7. Do not output images in chat. The image will be displayed in the UI.
    8. Answer in {{ language }} language.
    """

    user_prompt = """
    {{ query }}
    """

class BasicMountainChat(ChatInterface):
    """Basic mountain hiking assistant with tools."""

    def __init__(self) -> None:
        self.model_name = "gpt-4o-2024-08-06"
        self.llm = LiteLLM(model_name=self.model_name, use_structured_output=True)

        # Create agent with real tools
        self.agent = Agent(
            llm=self.llm,
            prompt=GeneralAssistantPrompt,
            tools=[
                get_web_search_tool(self.model_name),
                get_image_generation_tool(self.model_name),
            ],
        )

    async def chat(
        self,
        message: str,
        history: ChatFormat,
        context: ChatContext,
    ) -> AsyncGenerator[ChatResponse, None]:
        # Basic streaming implementation
        stream = self.agent.run_streaming(
            GeneralAssistantPromptInput(
                query=message,
                language="English"  # Default language for now
            )
        )

        async for response in stream:
            match response:
                case str():
                    # Regular text content from the LLM
                    if response.strip():  # Only yield non-empty text
                        yield self.create_text_response(response)
```

**How this works:**

- **Domain Expertise**: The prompt specializes the agent in mountain hiking, giving it focused knowledge
- **Tool Integration**: We configure web search and image generation tools that the agent can use
- **Streaming**: The agent streams responses in real-time as they're generated
- **Language Support**: Input includes language parameter for internationalization

Test this basic version:

```bash
ragbits api run mountain_chat:BasicMountainChat
```

!!! info "Why Start Simple"
Starting with a basic implementation helps you understand the core concepts before adding complexity. The agent already has access to powerful tools but we'll add UI feedback in the next steps.

## Step 2: Adding Live Updates for Tool Execution

Now let's add live updates so users can see when tools are being executed. This provides real-time feedback during potentially long-running operations like web searches or image generation.

Add these methods to your `BasicMountainChat` class:

```python
class BasicMountainChat(ChatInterface):
    # ... previous code ...

    @staticmethod
    def _get_tool_display_name(tool_name: str) -> str:
        """Get user-friendly display names for tools."""
        return {
            "search_web": "🔍 Web Search",
            "image_generation": "🎨 Image Generator"
        }.get(tool_name, tool_name)

    async def _handle_tool_call(self, response: ToolCall) -> ChatResponse:
        """Handle tool call and return live update."""
        tool_display_name = self._get_tool_display_name(response.name)
        return self.create_live_update(
            response.id,
            LiveUpdateType.START,
            f"Using {tool_display_name}",
            "Processing your request..."
        )

    async def _handle_tool_result(self, response: ToolCallResult) -> AsyncGenerator[ChatResponse, None]:
        """Handle tool call result and yield appropriate responses."""
        tool_display_name = self._get_tool_display_name(response.name)

        # Signal completion
        yield self.create_live_update(
            response.id,
            LiveUpdateType.FINISH,
            f"{tool_display_name} completed",
        )

    async def chat(
        self,
        message: str,
        history: ChatFormat,
        context: ChatContext,
    ) -> AsyncGenerator[ChatResponse, None]:
        # Enhanced streaming with tool handling
        stream = self.agent.run_streaming(
            GeneralAssistantPromptInput(
                query=message,
                language="English"
            )
        )

        async for response in stream:
            match response:
                case str():
                    # Regular text content from the LLM
                    if response.strip():
                        yield self.create_text_response(response)

                case ToolCall():
                    # Tool is being called - show live update
                    yield await self._handle_tool_call(response)

                case ToolCallResult():
                    # Tool completed - process results
                    async for result_response in self._handle_tool_result(response):
                        yield result_response
```

**How live updates work:**

- **ToolCall Detection**: When the agent decides to use a tool, we catch the `ToolCall` object
- **Start Indicator**: Show a "Using [Tool Name]" message with a processing indicator
- **Completion Signal**: When the tool finishes, show a completion message
- **User Experience**: Users see real-time progress instead of waiting in silence

Test the enhanced version:

```bash
ragbits api run mountain_chat:BasicMountainChat
```

Try asking: "Search for information about Mount Everest weather" and watch the live updates appear!

## Step 3: Processing Web Search Results

Now let's add automatic extraction of web search references. When the web search tool returns results, we'll extract URLs and display them as clickable references in the chat.

Add this method to handle web search results:

```python
class BasicMountainChat(ChatInterface):
    # ... previous code ...

    async def _extract_web_references(self, response: ToolCallResult) -> AsyncGenerator[ChatResponse, None]:
        """Extract URL citations from web search results."""
        for item in response.result.output:
            if item.type == "message":
                for content in item.content:
                    for annotation in content.annotations:
                        if annotation.type == "url_citation" and annotation.title and annotation.url:
                            yield self.create_reference(
                                title=annotation.title,
                                url=annotation.url,
                                content=""
                            )

    async def _handle_tool_result(self, response: ToolCallResult) -> AsyncGenerator[ChatResponse, None]:
        """Handle tool call result and yield appropriate responses."""
        tool_display_name = self._get_tool_display_name(response.name)

        # Signal completion
        yield self.create_live_update(
            response.id,
            LiveUpdateType.FINISH,
            f"{tool_display_name} completed",
        )

        # Process specific tool results
        if response.name == "search_web":
            async for reference in self._extract_web_references(response):
                yield reference
```

**How web reference extraction works:**

- **Result Processing**: After web search completes, we examine the tool result
- **Annotation Parsing**: Web search results contain annotations with URL citations
- **Reference Creation**: Each citation becomes a clickable reference in the chat UI
- **Automatic Display**: Users see relevant links without manual processing

The web search tool returns structured data with:

- **URLs**: Direct links to relevant web pages
- **Titles**: Descriptive titles for each reference
- **Annotations**: Metadata about why each link is relevant

Test web search with references:

```bash
ragbits api run mountain_chat:BasicMountainChat
```

Try: "Search for the best hiking trails in the Alps" and you'll see both the AI response and clickable reference links!

## Step 4: Adding Image Generation Support

Now let's add support for image generation with proper base64 encoding and display. When the image generation tool creates images, we'll handle the file processing and convert them for display in the chat.

Add this method to handle image generation results:

```python
class BasicMountainChat(ChatInterface):
    # ... previous code ...

    async def _create_image_response(self, image_path: Path) -> ChatResponse:
        """Create image response from file path."""
        with open(image_path, "rb") as image_file:
            image_filename = image_path.name
            base64_image = base64.b64encode(image_file.read()).decode("utf-8")
            return self.create_image_response(
                image_filename,
                f"data:image/png;base64,{base64_image}"
            )

    async def _handle_tool_result(self, response: ToolCallResult) -> AsyncGenerator[ChatResponse, None]:
        """Handle tool call result and yield appropriate responses."""
        tool_display_name = self._get_tool_display_name(response.name)

        # Signal completion
        yield self.create_live_update(
            response.id,
            LiveUpdateType.FINISH,
            f"{tool_display_name} completed",
        )

        # Process specific tool results
        if response.name == "search_web":
            async for reference in self._extract_web_references(response):
                yield reference
        elif response.name == "image_generation" and response.result.image_path:
            yield await self._create_image_response(response.result.image_path)
```

**How image generation works:**

- **Tool Execution**: The agent calls the image generation tool with a text prompt
- **File Creation**: The tool generates an image and saves it to a temporary file
- **Base64 Encoding**: We read the image file and convert it to base64 format
- **Data URL**: Create a proper data URL with MIME type for browser display
- **Automatic Chunking**: Large images are automatically chunked by the API for efficient transmission

The image generation process:

1. **Agent Decision**: Agent determines an image would be helpful
2. **Tool Call**: Calls image generation with descriptive prompt
3. **AI Generation**: Uses AI image model (like DALL-E) to create the image
4. **File Processing**: Converts generated image to base64 for web display
5. **UI Display**: Image appears directly in the chat interface

Test image generation:

```bash
ragbits api run mountain_chat:BasicMountainChat
```

Try: "Generate an image of mountain hiking gear" and watch the AI create a custom image!

## Step 5: Adding UI Customization and User Settings

Now let's add a polished UI with custom branding, user settings, and conversation history. This transforms our basic chat into a professional-looking application.

Add user settings and UI customization:

```python
from ragbits.chat.interface.forms import FeedbackConfig, UserSettings
from ragbits.chat.interface.ui_customization import HeaderCustomization, PageMetaCustomization, UICustomization

# Define user settings form
class UserSettingsFormExample(BaseModel):
    """User preferences for the chat interface."""
    model_config = ConfigDict(title="Chat Settings", json_schema_serialization_defaults_required=True)

    language: Literal["English", "Polish"] = Field(
        description="Please select the language",
        default="English"
    )

class MountainChatWithUI(ChatInterface):
    """Enhanced mountain hiking assistant with custom UI."""

    # Customize the UI appearance
    ui_customization = UICustomization(
        header=HeaderCustomization(
            title="🏔️ Mountain Hiking Assistant",
            subtitle="by Ragbits",
            logo="🥾"
        ),
        welcome_message=(
            "🏔️ **Welcome to your Mountain Hiking Assistant!**\n\n"
            "I can help you with:\n"
            "- **Web Search** for hiking information, weather, trails\n"
            "- **Image Generation** for visualizing routes, gear, or concepts\n\n"
            "Ask me anything about mountain hiking!"
        ),
        meta=PageMetaCustomization(favicon="🏔️", page_title="Mountain Hiking Assistant"),
    )

    # Add user settings
    user_settings = UserSettings(form=UserSettingsFormExample)

    # Enable features
    conversation_history = True
    show_usage = True

    def __init__(self) -> None:
        self.model_name = "gpt-4o-2024-08-06"
        self.llm = LiteLLM(model_name=self.model_name, use_structured_output=True)

        self.agent = Agent(
            llm=self.llm,
            prompt=GeneralAssistantPrompt,
            tools=[
                get_web_search_tool(self.model_name),
                get_image_generation_tool(self.model_name),
            ],
        )

    # ... (include all the tool handling methods from previous steps) ...

    async def chat(
        self,
        message: str,
        history: ChatFormat,
        context: ChatContext,
    ) -> AsyncGenerator[ChatResponse, None]:
        # Get user language preference
        language = "English"
        if context and context.user_settings:
            language = context.user_settings.get("language", "English")

        # Create streaming response from agent
        stream = self.agent.run_streaming(
            GeneralAssistantPromptInput(
                query=message,
                language=language
            )
        )

        # Process streaming responses (same pattern as before)
        async for response in stream:
            match response:
                case str():
                    if response.strip():
                        yield self.create_text_response(response)
                case ToolCall():
                    yield await self._handle_tool_call(response)
                case ToolCallResult():
                    async for result_response in self._handle_tool_result(response):
                        yield result_response
```

**UI customization features:**

- **Custom Header**: Branded title, subtitle, and logo
- **Welcome Message**: Markdown-formatted introduction with feature overview
- **Page Metadata**: Custom favicon and page title for browser tabs
- **User Settings**: Language preference that affects agent responses
- **Conversation History**: Persistent chat history across sessions
- **Usage Tracking**: Token usage display for monitoring costs

Test the enhanced UI:

```bash
ragbits api run mountain_chat:MountainChatWithUI
```

You'll see a professional-looking interface with custom branding and user settings!

## Step 6: Adding Authentication and Feedback Forms

For production applications, you'll want authentication and user feedback. Let's add these final features to create a complete, secure chat interface.

Add feedback forms and authentication:

```python
from ragbits.chat.auth import ListAuthenticationBackend

# Define feedback forms
class LikeFormExample(BaseModel):
    """Form for positive feedback."""
    model_config = ConfigDict(
        title="Like Form",
        json_schema_serialization_defaults_required=True,
    )

    like_reason: str = Field(
        description="Why do you like this?",
        min_length=1,
    )

class DislikeFormExample(BaseModel):
    """Form for negative feedback."""
    model_config = ConfigDict(
        title="Dislike Form",
        json_schema_serialization_defaults_required=True
    )

    issue_type: Literal["Incorrect information", "Not helpful", "Unclear", "Other"] = Field(
        description="What was the issue?"
    )
    feedback: str = Field(description="Please provide more details", min_length=1)

class AuthenticatedMountainChat(ChatInterface):
    """Complete mountain hiking assistant with authentication."""

    ui_customization = UICustomization(
        header=HeaderCustomization(
            title="🔐 Authenticated Mountain Assistant",
            subtitle="by Ragbits",
            logo="🥾"
        ),
        welcome_message=(
            "🔐 **Welcome to Authenticated Mountain Assistant!**\n\n"
            "You can ask me **anything** about mountain hiking! \n\n"
            "I can also generate images for you.\n\n"
            "Please log in to start chatting!"
        ),
        meta=PageMetaCustomization(favicon="🏔️", page_title="Mountain Assistant"),
    )

    # Configure feedback system
    feedback_config = FeedbackConfig(
        like_enabled=True,
        like_form=LikeFormExample,
        dislike_enabled=True,
        dislike_form=DislikeFormExample,
    )

    # Add user settings and features
    user_settings = UserSettings(form=UserSettingsFormExample)
    conversation_history = True
    show_usage = True

    def __init__(self) -> None:
        self.model_name = "gpt-4o-2024-08-06"
        self.llm = LiteLLM(model_name=self.model_name, use_structured_output=True)
        self.agent = Agent(
            llm=self.llm,
            prompt=GeneralAssistantPrompt,
            tools=[
                get_web_search_tool(self.model_name),
                get_image_generation_tool(self.model_name),
            ],
        )

    # ... (include all the tool handling methods from previous steps) ...

    async def chat(
        self,
        message: str,
        history: ChatFormat,
        context: ChatContext,
    ) -> AsyncGenerator[ChatResponse, None]:
        # Check authentication
        user_info = context.user

        if not user_info:
            yield self.create_text_response("⚠️ Authentication information not found.")
            return

        # Get user language preference
        language = context.user_settings.get("language", "English") if context else "English"

        # Process with agent (same as before)
        stream = self.agent.run_streaming(
            GeneralAssistantPromptInput(query=message, language=language)
        )

        async for response in stream:
            match response:
                case str():
                    if response.strip():
                        yield self.create_text_response(response)
                case ToolCall():
                    yield await self._handle_tool_call(response)
                case ToolCallResult():
                    async for result_response in self._handle_tool_result(response):
                        yield result_response

# Create authentication backend
def get_auth_backend() -> ListAuthenticationBackend:
    """Factory function to create the authentication backend."""
    users = [
        {
            "user_id": "8e6c5871-3817-4d62-828f-ef6789de31b9",
            "username": "test",
            "password": "test123",
            "email": "test@example.com",
            "full_name": "Test User",
            "roles": ["user"],
            "metadata": {"department": "Hiking", "clearance_level": "standard"},
        },
    ]
    return ListAuthenticationBackend(users)
```

**Authentication and feedback features:**

- **User Authentication**: Secure login system with user management
- **Feedback Forms**: Structured feedback collection with like/dislike options
- **User Context**: Access to authenticated user information in chat logic
- **Session Management**: Automatic session handling and token validation

Launch with authentication:

```bash
ragbits api run mountain_chat:AuthenticatedMountainChat --auth mountain_chat:get_auth_backend
```

Login credentials:

- Username: `test`
- Password: `test123`

## Enabling Debug Mode

Debug mode provides detailed information about tool calls and agent decisions:

```bash
ragbits api run mountain_chat:AuthenticatedMountainChat --auth mountain_chat:get_auth_backend --debug
```

With debug mode enabled:

- Debug panel shows tool execution details
- Agent decision-making process is visible
- Token usage and performance metrics displayed
- Error information is comprehensive

Additional server options:

```bash
# Custom host and port
ragbits api run mountain_chat:AuthenticatedMountainChat --host 0.0.0.0 --port 9000

# Enable CORS for development
ragbits api run mountain_chat:AuthenticatedMountainChat --cors-origin http://localhost:3000
```

## Complete Working Example

Here's your complete `mountain_chat.py` file with all features:

```python
"""
Complete Mountain Hiking Assistant with Tools, Authentication, and UI Customization
"""

import base64
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ragbits.agents import Agent, ToolCallResult
from ragbits.agents.tools.openai import get_image_generation_tool, get_web_search_tool
from ragbits.chat.auth import ListAuthenticationBackend
from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.forms import FeedbackConfig, UserSettings
from ragbits.chat.interface.types import ChatContext, ChatResponse, LiveUpdateType, Message
from ragbits.chat.interface.ui_customization import HeaderCustomization, PageMetaCustomization, UICustomization
from ragbits.core.llms import LiteLLM, ToolCall
from ragbits.core.prompt import Prompt

# Forms
class LikeFormExample(BaseModel):
    model_config = ConfigDict(title="Like Form", json_schema_serialization_defaults_required=True)
    like_reason: str = Field(description="Why do you like this?", min_length=1)

class DislikeFormExample(BaseModel):
    model_config = ConfigDict(title="Dislike Form", json_schema_serialization_defaults_required=True)
    issue_type: Literal["Incorrect information", "Not helpful", "Unclear", "Other"] = Field(description="What was the issue?")
    feedback: str = Field(description="Please provide more details", min_length=1)

class UserSettingsFormExample(BaseModel):
    model_config = ConfigDict(title="Chat Settings", json_schema_serialization_defaults_required=True)
    language: Literal["English", "Polish"] = Field(description="Please select the language", default="English")

# Agent prompt
class GeneralAssistantPromptInput(BaseModel):
    query: str
    language: str

class GeneralAssistantPrompt(Prompt[GeneralAssistantPromptInput]):
    system_prompt = """
    You are a helpful assistant that is expert in mountain hiking and answers user questions.
    You have access to the following tools: web search and image generation.

    Guidelines:
    1. Use the web search tool when the user asks for factual information, research, or current events.
    2. Use the image generation tool when the user asks to create, generate, draw, or produce images.
    3. The image generation tool generates images in 512x512 resolution.
    4. Return the image as a base64 encoded string in the response.
    5. Always select the most appropriate tool based on the user's request.
    6. If the user asks explicitly for a picture, use only the image generation tool.
    7. Do not output images in chat. The image will be displayed in the UI.
    8. Answer in {{ language }} language.
    """
    user_prompt = "{{ query }}"

class MyChat(ChatInterface):
    """Complete mountain hiking assistant with all features."""

    ui_customization = UICustomization(
        header=HeaderCustomization(title="🔐 Authenticated Mountain Assistant", subtitle="by Ragbits", logo="🥾"),
        welcome_message=(
            "🔐 **Welcome to Authenticated Mountain Assistant!**\n\n"
            "You can ask me **anything** about mountain hiking! \n\n Also I can generate images for you.\n\n"
            "Please log in to start chatting!"
        ),
        meta=PageMetaCustomization(favicon="🏔️", page_title="Mountain Assistant"),
    )

    feedback_config = FeedbackConfig(
        like_enabled=True, like_form=LikeFormExample,
        dislike_enabled=True, dislike_form=DislikeFormExample,
    )
    user_settings = UserSettings(form=UserSettingsFormExample)
    conversation_history = True
    show_usage = True

    def __init__(self) -> None:
        self.model_name = "gpt-4o-2024-08-06"
        self.llm = LiteLLM(model_name=self.model_name, use_structured_output=True)
        self.agent = Agent(llm=self.llm, prompt=GeneralAssistantPrompt, tools=[
            get_web_search_tool(self.model_name), get_image_generation_tool(self.model_name),
        ])

    @staticmethod
    def _get_tool_display_name(tool_name: str) -> str:
        return {"search_web": "🔍 Web Search", "image_generation": "🎨 Image Generator"}.get(tool_name, tool_name)

    async def _handle_tool_call(self, response: ToolCall) -> ChatResponse:
        tool_display_name = self._get_tool_display_name(response.name)
        return self.create_live_update(response.id, LiveUpdateType.START, f"Using {tool_display_name}", "Processing your request...")

    async def _handle_tool_result(self, response: ToolCallResult) -> AsyncGenerator[ChatResponse, None]:
        tool_display_name = self._get_tool_display_name(response.name)
        yield self.create_live_update(response.id, LiveUpdateType.FINISH, f"{tool_display_name} completed")

        if response.name == "search_web":
            async for reference in self._extract_web_references(response):
                yield reference
        elif response.name == "image_generation" and response.result.image_path:
            yield await self._create_image_response(response.result.image_path)

    async def _extract_web_references(self, response: ToolCallResult) -> AsyncGenerator[ChatResponse, None]:
        for item in response.result.output:
            if item.type == "message":
                for content in item.content:
                    for annotation in content.annotations:
                        if annotation.type == "url_citation" and annotation.title and annotation.url:
                            yield self.create_reference(title=annotation.title, url=annotation.url, content="")

    async def _create_image_response(self, image_path: Path) -> ChatResponse:
        with open(image_path, "rb") as image_file:
            image_filename = image_path.name
            base64_image = base64.b64encode(image_file.read()).decode("utf-8")
            return self.create_image_response(image_filename, f"data:image/png;base64,{base64_image}")

    async def chat(self, message: str, history: ChatFormat, context: ChatContext) -> AsyncGenerator[ChatResponse, None]:
        user_info = context.user
        if not user_info:
            yield self.create_text_response("⚠️ Authentication information not found.")
            return

        stream = self.agent.run_streaming(GeneralAssistantPromptInput(
            query=message, language=context.user_settings["language"]
        ))

        async for response in stream:
            match response:
                case str():
                    if response.strip():
                        yield self.create_text_response(response)
                case ToolCall():
                    yield await self._handle_tool_call(response)
                case ToolCallResult():
                    async for result_response in self._handle_tool_result(response):
                        yield result_response

def get_auth_backend() -> ListAuthenticationBackend:
    users = [{"user_id": "8e6c5871-3817-4d62-828f-ef6789de31b9", "username": "test", "password": "test123",
              "email": "test@example.com", "full_name": "Test User", "roles": ["user"],
              "metadata": {"department": "Hiking", "clearance_level": "standard"}}]
    return ListAuthenticationBackend(users)
```

## Conclusions

In this tutorial, we've built a sophisticated chat interface using **real AI tools** for web search and image generation, providing actual capabilities rather than simulated responses.

### Key Features Implemented

- **🔍 Real Web Search**: Live web search with automatic reference extraction
- **🎨 Real Image Generation**: AI-powered image creation with base64 encoding
- **⚡ Live Updates**: Real-time progress indicators during tool execution
- **🔐 Authentication**: Secure login system with user management
- **📝 User Forms**: Feedback collection and language preferences
- **🎨 UI Customization**: Branded interface with welcome messages
- **📊 Usage Tracking**: Token usage and conversation history

### Why This Approach Works

1. **Real Capabilities**: Tools perform actual web searches and generate real images
2. **Live Feedback**: Users see progress as tools execute, improving UX
3. **Automatic Processing**: Web references extracted automatically from search results
4. **Flexible Tools**: Easy to add more tools (database queries, API calls, etc.)
5. **Production Ready**: Built-in authentication, error handling, and monitoring

### Next Steps

Now you can build tool-powered chat interfaces with real capabilities! You can:

- **Add More Tools**: Create custom tools for specific domains
- **Enhance Authentication**: Connect to external auth providers
- **Integrate Databases**: Add tools for data retrieval and storage
- **Connect APIs**: Use tools to integrate with external services
- **Add Document Search**: Connect to [Document Search](./rag.md) for knowledge bases

The key insight: **use real tools that provide actual capabilities** rather than simulated responses. This creates chat interfaces that can truly help users accomplish tasks.

For more advanced configurations and deployment options, check out the [Chat API How-To Guide](../how-to/chatbots/api.md).
