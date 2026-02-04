"""
Ragbits Chat Example: Tutorial Chat Interface

This example demonstrates how to use the `ChatInterface` to create a chat application

It showcases different functionalities including:
- authentication
- user settings
- feedback
- live updates
- reference web search results
- image generation

It showcases different chat response types including:
- text responses
- live updates
- reference web search results
- image generation

To run the script, execute the following command:

    ```bash
    ragbits api run examples.chat.tutorial:MyChat --auth examples.chat.tutorial:get_auth_backend --debug
    ```
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-chat",
#     "ragbits-agents"
# ]
# ///
#

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
from ragbits.chat.interface.types import ChatContext, ChatResponse, LiveUpdateType
from ragbits.chat.interface.ui_customization import HeaderCustomization, PageMetaCustomization, UICustomization
from ragbits.core.llms import LiteLLM, ToolCall
from ragbits.core.prompt import Prompt
from ragbits.core.prompt.base import ChatFormat


class LikeFormExample(BaseModel):
    """A simple example implementation of the like form that demonstrates how to use Pydantic for form definition."""

    model_config = ConfigDict(
        title="Like Form",
        json_schema_serialization_defaults_required=True,
    )

    like_reason: str = Field(
        description="Why do you like this?",
        min_length=1,
    )


class DislikeFormExample(BaseModel):
    """A simple example implementation of the dislike form that demonstrates how to use Pydantic for form definition."""

    model_config = ConfigDict(title="Dislike Form", json_schema_serialization_defaults_required=True)

    issue_type: Literal["Incorrect information", "Not helpful", "Unclear", "Other"] = Field(
        description="What was the issue?"
    )
    feedback: str = Field(description="Please provide more details", min_length=1)


class UserSettingsFormExample(BaseModel):
    """A simple example implementation of the chat form that demonstrates how to use Pydantic for form definition."""

    model_config = ConfigDict(title="Chat Form", json_schema_serialization_defaults_required=True)

    language: Literal["English", "Polish"] = Field(description="Please select the language", default="English")


class GeneralAssistantPromptInput(BaseModel):
    """
    Input format for the General Assistant Prompt.
    """

    query: str
    language: str


class GeneralAssistantPrompt(Prompt[GeneralAssistantPromptInput]):
    """
    Prompt that responds to user queries using appropriate tools.
    """

    system_prompt = """
    You are a helpful assistant that is expert in mountain hiking and answers user questions.
    You have access to the following tools: web search and image generation.

    Guidelines:
    1. Use the web search tool when the user asks for factual information, research, or current events.
    2. Use the image generation tool when the user asks to create, generate, draw, or produce images.
    3. The image generation tool generates images in 512x512 resolution.
    4. Return the image as a base64 encoded string in the response.
    5. Always select the most appropriate tool based on the user’s request.
    6. If the user asks explicity for a picture, use only the image generation tool.
    7. Do not output images in chat. The image will be displayed in the UI.
    8. Answer in {{ language }} language.
    """

    user_prompt = """
    {{ query }}
    """


class MyChat(ChatInterface):
    """A simple example implementation of the ChatInterface that demonstrates different response types."""

    ui_customization = UICustomization(
        header=HeaderCustomization(title="Authenticated Tutorial Ragbits Chat", subtitle="by deepsense.ai", logo="🐰"),
        welcome_message=(
            "🔐 **Welcome to Authenticated Tutorial Ragbits Chat!**\n\n"
            "You can ask me **anything** about mountain hiking! \n\n Also I can generate images for you.\n\n"
            "Please log in to start chatting!"
        ),
        meta=PageMetaCustomization(favicon="🔨", page_title="Change me!"),
    )

    feedback_config = FeedbackConfig(
        like_enabled=True,
        like_form=LikeFormExample,
        dislike_enabled=True,
        dislike_form=DislikeFormExample,
    )
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

    @staticmethod
    def _get_tool_display_name(tool_name: str) -> str:
        """Get display name for a tool."""
        return {"search_web": "🔍 Web Search", "image_generation": "🎨 Image Generator"}.get(tool_name, tool_name)

    async def _handle_tool_call(self, response: ToolCall) -> ChatResponse:
        """Handle tool call and return live update."""
        tool_display_name = self._get_tool_display_name(response.name)
        return self.create_live_update(
            response.id, LiveUpdateType.START, f"Using {tool_display_name}", "Processing your request..."
        )

    async def _handle_tool_result(self, response: ToolCallResult) -> AsyncGenerator[ChatResponse, None]:
        """Handle tool call result and yield appropriate responses."""
        tool_display_name = self._get_tool_display_name(response.name)

        yield self.create_live_update(
            response.id,
            LiveUpdateType.FINISH,
            f"{tool_display_name} completed",
        )

        if response.name == "search_web":
            async for reference in self._extract_web_references(response):
                yield reference
        elif response.name == "image_generation" and response.result.image_path:
            yield await self._create_image_response(response.result.image_path)

    async def _extract_web_references(self, response: ToolCallResult) -> AsyncGenerator[ChatResponse, None]:
        """Extract URL citations from web search results."""
        for item in response.result.output:
            if item.type == "message":
                for content in item.content:
                    for annotation in content.annotations:
                        if annotation.type == "url_citation" and annotation.title and annotation.url:
                            yield self.create_reference(title=annotation.title, url=annotation.url, content="")

    async def _create_image_response(self, image_path: Path) -> ChatResponse:
        """Create image response from file path."""
        with open(image_path, "rb") as image_file:
            image_filename = image_path.name
            base64_image = base64.b64encode(image_file.read()).decode("utf-8")
            return self.create_image_response(image_filename, f"data:image/png;base64,{base64_image}")

    async def chat(
        self,
        message: str,
        history: ChatFormat,
        context: ChatContext,
    ) -> AsyncGenerator[ChatResponse, None]:
        """
        Example implementation of the ChatInterface.

        Args:
            message: The current user message
            history: Optional list of previous messages in the conversation
            context: Optional context

        Yields:
            ChatResponse objects containing different types of content:
            - Text chunks for the actual response
            - Image responses with base64 data URLs
            - Live updates for tool execution status
        """
        # Get authenticated user info
        user_info = context.user

        if not user_info:
            yield self.create_text_response("⚠️ Authentication information not found.")
            return

        stream = self.agent.run_streaming(
            GeneralAssistantPromptInput(query=message, language=context.user_settings["language"])
        )

        async for response in stream:
            match response:
                case str():
                    # Regular text content from the LLM
                    if response.strip():  # Only yield non-empty text
                        yield self.create_text_response(response)

                case ToolCall():
                    yield await self._handle_tool_call(response)

                case ToolCallResult():
                    async for result_response in self._handle_tool_result(response):
                        yield result_response


def get_auth_backend() -> ListAuthenticationBackend:
    """Factory function to create the preferred authentication backend."""
    users = [
        {
            "user_id": "8e6c5871-3817-4d62-828f-ef6789de31b9",
            "username": "test",
            "password": "test123",
            "email": "test@example.com",
            "full_name": "Test User",
            "roles": ["user"],
            "metadata": {"department": "Test", "clearance_level": "low"},
        },
    ]

    return ListAuthenticationBackend(users)
