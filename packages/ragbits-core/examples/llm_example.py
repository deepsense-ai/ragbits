# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits[litellm]",
# ]
# ///
import asyncio

from pydantic import BaseModel

from ragbits.core.llms.litellm import LiteLLM
from ragbits.core.prompt import Prompt


class LoremPromptInput(BaseModel):
    """
    Input format for the LoremPrompt.
    """

    theme: str
    pun_allowed: bool = False


class LoremPromptOutput(BaseModel):
    """
    Output format for the LoremPrompt.
    """

    joke: str
    joke_category: str


class JokePrompt(Prompt[LoremPromptInput, LoremPromptOutput]):
    """
    A prompt that generates jokes.
    """

    system_prompt = """
    You are a joke generator. The jokes you generate should be funny and not offensive. {% if not pun_allowed %}Also, make sure
    that the jokes do not contain any puns.{% else %}You can use any type of joke, even if it contains puns.{% endif %}

    Respond as json with two fields: joke and joke_category.
    """

    user_prompt = """
     theme: {{ theme }}
    """


async def main():
    """
    Example of using the LiteLLM client with a Prompt class. Requires the OPENAI_API_KEY environment variable to be set.
    """
    llm = LiteLLM("gpt-4o-2024-08-06", use_structured_output=True)
    prompt = JokePrompt(LoremPromptInput(theme="software developers", pun_allowed=True))
    response = await llm.generate(prompt)
    print(f"The LLM generated a (hopefully) funny {response.joke_category} joke:")
    print(response.joke)


if __name__ == "__main__":
    asyncio.run(main())
