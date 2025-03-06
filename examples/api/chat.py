# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-api",
# ]
# ///
import asyncio
import os

from pydantic import BaseModel

from ragbits.core.llms.litellm import LiteLLM
from ragbits.core.prompt import Prompt


class ChatInput(BaseModel):
    """
    Input format for the Chat message.
    """

    question: str


class ChatOutput(BaseModel):
    """
    Output format for the Chat message.
    """

    answer: str


class ChatPrompt(Prompt[ChatInput, ChatOutput]):
    """
    A prompt that generates answers for asked questions.
    """

    system_prompt = """
    You are a wise person that answers questions. The answer should be serious and true
    """

    user_prompt = """
     question: {{ question }}
    """


async def main(question: str) -> None:
    """
    Example of using the LiteLLM client with a Chat class. Requires the OPENAI_API_KEY environment variable to be set.
    """
    llm = LiteLLM("gpt-4o-2024-08-06", use_structured_output=True)
    prompt = ChatPrompt(ChatInput(question=question))
    response = await llm.generate(prompt)

    return response.answer


if __name__ == "__main__":
    asyncio.run(main())
