# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-core",
# ]
# ///
import asyncio

from pydantic import BaseModel

from ragbits.core.llms.litellm import LiteLLM
from ragbits.core.prompt import Prompt


class AnimalNamePromptInput(BaseModel):
    """
    Input format for the AnimalNamePromptInput.
    """

    animal: str


class AnimalNameOutput(BaseModel):
    """
    Output format for the AnimalNamePromptPrompt.
    """

    name: str


class AnimalPrompt(Prompt[AnimalNamePromptInput, AnimalNameOutput]):
    """
    A prompt that generates animal names.
    """

    system_prompt = """
    You are an animal name generator. The jokes you generate should be appropriate. Use provided animal kind as a base.
    """

    user_prompt = """
     animal: {{ animal }}
    """

    few_shots = [(AnimalNamePromptInput(animal="dog"), AnimalNameOutput(name="Fluffy"))]


async def main() -> None:
    """
    Example of using the LiteLLM client with an AnimalPrompt class. Requires the OPENAI_API_KEY environment variable
    to be set.
    """
    llm = LiteLLM("gpt-4o-2024-08-06", use_structured_output=True)
    animal = "cat"
    prompt = AnimalPrompt(AnimalNamePromptInput(animal=animal))
    response = await llm.generate(prompt)
    print(f"The LLM generated decided to name {animal} as {response.name}")


if __name__ == "__main__":
    asyncio.run(main())
