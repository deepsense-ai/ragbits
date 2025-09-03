
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

import base64
from collections.abc import AsyncGenerator

from pydantic import BaseModel

from ragbits.agents import Agent, ToolCallResult
from ragbits.agents.tools.openai import get_image_generation_tool, get_web_search_tool
from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import ChatContext, ChatResponse, LiveUpdateType, Message
from ragbits.core.llms import LiteLLM, ToolCall
from ragbits.core.prompt import Prompt


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
                        "Processing your request..."
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
                        # Extract URL citations from the response
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

                    if response.name == "image_generation" and response.result["image_path"]:
                        with open(response.result["image_path"], "rb") as image_file:
                            image_filename = response.result["image_path"].name
                            base64_image = base64.b64encode(image_file.read()).decode("utf-8")
                            yield self.create_image_response(
                                    image_filename,
                                    f"data:image/png;base64,{base64_image}"
                                )

