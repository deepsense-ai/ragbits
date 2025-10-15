"""
Example chat implementation with custom theme support.

SUPER EASY USAGE:
1. Go to https://www.heroui.com/themes
2. Create your theme
3. Copy the JSON configuration
4. Save it as 'my-theme.json'
5. Run: ragbits api run examples.chat.themed_chat:MyChat --theme my-theme.json

That's it! No manual conversion needed!
"""

from collections.abc import AsyncGenerator

from pydantic import BaseModel

from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import ChatContext, ChatResponse
from ragbits.core.llms.litellm import LiteLLM
from ragbits.core.prompt import Prompt


class SimplePromptInput(BaseModel):
    """Input for the simple chat prompt."""

    query: str


class SimplePrompt(Prompt[SimplePromptInput]):
    """Simple chat prompt with theme support."""

    system_prompt = "You are a helpful assistant with a custom theme."
    user_prompt = "User: {{ query }}"


class MyChat(ChatInterface):
    """Chat interface implementation with custom theme support."""

    def __init__(self):
        self.llm = LiteLLM("gpt-3.5-turbo")

    async def chat(self, message: str, history: list[dict], context: ChatContext) -> AsyncGenerator[ChatResponse, None]:
        """Handle chat messages and return streaming responses."""
        prompt_input = SimplePromptInput(query=message)
        prompt = SimplePrompt(prompt_input)
        response = await self.llm.generate(prompt)

        yield ChatInterface.create_text_response(str(response))
