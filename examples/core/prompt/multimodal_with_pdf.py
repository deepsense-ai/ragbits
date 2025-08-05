"""
Ragbits Core Example: Multimodal Prompt with PDF Input

This example demonstrates how to use the `Prompt` class with both text and PDF inputs.
We define a `DocumentPrompt` that answers the question based on a provided PDF document.

To run the script, execute the following command:

    ```bash
    uv run examples/core/prompt/multimodal_with_pdf.py
    ```
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-core",
# ]
# ///

import asyncio

from pydantic import BaseModel

from ragbits.core.llms import LiteLLM
from ragbits.core.prompt import Attachment, Prompt


class DocumentPromptInput(BaseModel):
    """
    Input format for the DocumentPrompt.
    """

    question: str
    document: Attachment


class DocumentPromptOutput(BaseModel):
    """
    Output format for the DocumentPrompt.
    """

    answer: str


class DocumentPrompt(Prompt[DocumentPromptInput, DocumentPromptOutput]):
    """
    Prompt that answers questions based on a provided book passage.
    """

    system_prompt = """
    You are a helpful assistant that answers questions based on the provided document.
    """

    user_prompt = """
    Question: {{ question }}
    """


async def main() -> None:
    """
    Run the example.
    """
    llm = LiteLLM(model_name="gpt-4o-2024-08-06", use_structured_output=True)
    document = Attachment(
        url="https://etc.usf.edu/lit2go/pdf/passage/1/alices-adventures-in-wonderland-001-chapter-i-down-the-rabbit-hole.pdf"
    )
    prompt_input = DocumentPromptInput(document=document, question="What happened to Alice?")
    prompt = DocumentPrompt(prompt_input)
    response = await llm.generate(prompt)
    print(response.answer)


if __name__ == "__main__":
    asyncio.run(main())
