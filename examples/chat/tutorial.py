
"""
Ragbits Chat Example: Chat Interface

This example demonstrates how to use the `ChatInterface` to create a simple chat application.
It showcases different response types, including text responses, live updates, and reference documents.

To run the script, execute the following command:

    ```bash
    ragbits api run examples.chat.test:MyChat
    ```
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-chat",
# ]
# ///
#

import os
import uuid
import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path

from pydantic import BaseModel

from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import ChatContext, ChatResponse, LiveUpdateType, Message
from ragbits.core.prompt import Prompt
from ragbits.agents import Agent, ToolCallResult
from ragbits.agents.tools import get_web_search_tool, get_image_generation_tool
from ragbits.core.llms import LiteLLM, ToolCall


class GeneralAssistantPromptInput(BaseModel):
    """
    Input format for the General Assistant Prompt.
    """

    query: str


class GeneralAssistantPrompt(Prompt[GeneralAssistantPromptInput]):
    """
    Prompt that responds to user queries using appropriate tools.
    """

    system_prompt = """
    You are a helpful assistant that responds to user questions.
    You have access to tools for web search and image generation.

    Guidelines for tool usage:
    - Use web search when the user asks for information, facts, current events, research, or needs to look something up
    - Use image generation when the user asks to create, generate, draw, make, or produce images/pictures
    - Choose the most appropriate tool based on the user's specific request
    - You can use only one tool per response - choose the most relevant one
    - Do not provide image data in the response or provide information about the image save in the file system, because the image is showed in the UI
    - Always generate 1024x1024 image
    - With web search, always return the sources of the informations in the response in additional key "references" in a list of objects with title, content and url
    """

    user_prompt = """
    {{ query }}
    """


class MyChat(ChatInterface):
    """A simple example implementation of the ChatInterface that demonstrates different response types."""

    def __init__(self) -> None:
        self.model_name = "gpt-4o-2024-08-06"
        self.llm = LiteLLM(model_name=self.model_name, use_structured_output=True)
        self.agent = Agent(llm=self.llm, prompt=GeneralAssistantPrompt, tools=[
            get_web_search_tool(self.model_name),
            get_image_generation_tool(self.model_name),
        ])

    async def chat(
        self,
        message: str,
        history: list[Message] | None = None,
        context: ChatContext | None = None,
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

        stream = self.agent.run_streaming(GeneralAssistantPromptInput(query=message))

        async for response in stream:
            print(response)
            match response:
                case str():
                    # Regular text content from the LLM
                    if response.strip():  # Only yield non-empty text
                        yield self.create_text_response(response)

                case ToolCall():
                    # Tool is starting to execute
                    tool_display_name = {
                        "search_web": "🔍 Web Search",
                        "image_generation": "🎨 Image Generator"
                    }.get(response.name, response.name)

                    yield self.create_live_update(
                        response.id,
                        LiveUpdateType.START,
                        f"Using {tool_display_name}",
                        f"Processing your request..."
                    )

                case ToolCallResult():
                    # Tool has finished executing
                    tool_display_name = {
                        "search_web": "🔍 Web Search",
                        "image_generation": "🎨 Image Generator"
                    }.get(response.name, response.name)

                    yield self.create_live_update(
                        response.id,
                        LiveUpdateType.FINISH,
                        f"{tool_display_name} completed",
                    )

                    if response.name == "search_web":
                        print(response.result)

                    # Handle different tool results
                    if response.name == "image_generation":
                        result_content = response.result
                        if isinstance(result_content, str):
                            # Look for image path in the result
                            image_path = response.arguments.get("save_path")

                            if image_path and os.path.exists(image_path):
                                try:
                                    # Generate unique filename for serving
                                    unique_filename = f"{uuid.uuid4()}.png"

                                    # You can either:
                                    # Option A: Move to a static directory that your web server serves
                                    static_dir = Path("packages/ragbits-chat/src/ragbits/chat/ui-build/static/images")
                                    static_dir.mkdir(parents=True, exist_ok=True)
                                    new_path = static_dir / unique_filename

                                    import shutil
                                    shutil.move(image_path, new_path)


                                    # Create URL for the static file
                                    image_url = f"/static/images/{unique_filename}"

                                    yield self.create_image_response(
                                        image_id=str(uuid.uuid4()),
                                        image_url=image_url
                                    )

                                except Exception as e:
                                    print(f"Error processing image: {e}")
                                    yield self.create_text_response("Sorry, there was an error processing the generated image.")
