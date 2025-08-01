# How-To: Use attachments in prompts with Ragbits

This guide will walk you through defining and using prompts in Ragbits that accept attachments as input.
It covers handling single and multiple attachment inputs, incorporating conditionals in prompt templates based on the presence of attachments, and using such prompts with an LLM.

Attachment types currently supported include standard image formats (such as JPEG, PNG) and PDF documents.

## How to define a prompt with an attachment input

The attachment is represented by the `prompt.Attachment` class.
It can be initialized in multiple ways depending on the source of the file data.
The class supports both binary data and URLs, with optional MIME type specification.

```python
from ragbits.core.prompt import Attachment

file_bytes = Attachment(data=b"file_bytes")
image_url = Attachment(url="http://image.jpg")
pdf_url = Attachment(url="http://document.pdf")
file_with_url_and_mime =  Attachment(url="http://address.pl/file_with_no_extension", mime_type="jpeg")
```

To define a prompt that takes an attachment as input, create a Pydantic model representing the input structure.
The model should include a field for the attachment that holds an instance of `prompt.Attachment` class - its name does not matter.

To pass multiple attachments, just define multiple fields of type `Attachment` or a single field that is a list of `Attachment` instances.


```python
import asyncio
from pydantic import BaseModel
from ragbits.core.prompt import Attachment, Prompt
from ragbits.core.llms.litellm import LiteLLM

class EmployeeOnboardingInput(BaseModel):
    """
    Input model for employee onboarding files.
    """
    headshot: Attachment
    contract: Attachment
    documents: list[Attachment]


class EmployeeOnboardingPrompt(Prompt):
    """
    A prompt to process employee onboarding files.
    """

    user_prompt = "Review the employee onboarding files and provide feedback."


async def main():
    llm = LiteLLM("gpt-4o")

    headshot = Attachment(data=b"<your_photo_here>")
    contract = Attachment(data=b"<your_contract_here>")
    documents = [
        Attachment(data=b"<your_document_1_here>"),
        Attachment(data=b"<your_document_2_here>"),
    ]
    prompt = EmployeeOnboardingPrompt(
        EmployeeOnboardingInput(headshot=headshot, contract=contract, documents=documents)
    )
    response = await llm.generate(prompt)
    print(response)


asyncio.run(main())
```

## Using conditionals in templates

Sometimes, you may want to modify the prompt based on whether an attachment is provided. Jinja conditionals can help achieve this.

```python
import asyncio
from pydantic import BaseModel
from ragbits.core.prompt import Attachment, Prompt
from ragbits.core.llms.litellm import LiteLLM

class QuestionWithOptionalPhotoInput(BaseModel):
    """
    Input model that optionally includes a photo.
    """
    question: str
    reference_photo: Attachment | None = None


class QuestionWithPhotoPrompt(Prompt[QuestionWithOptionalPhotoInput]):
    """
    A prompt that considers whether a photo is provided.
    """

    system_prompt = """
    You are a knowledgeable assistant providing detailed answers.
    If a photo is provided, use it as a reference for your response.
    """

    user_prompt = """
    User asked: {{ question }}
    {% if reference_photo %}
    Here is a reference photo: {{ reference_photo }}
    {% else %}
    No photo was provided.
    {% endif %}
    """


async def main():
    llm = LiteLLM("gpt-4o")
    input_with_photo = QuestionWithOptionalPhotoInput(
        question="What animal do you see in this photo?", reference_photo=Attachment(data=b"<your_photo_here>")
    )
    input_without_photo = QuestionWithOptionalPhotoInput(question="What is the capital of France?")

    print(await llm.generate(QuestionWithPhotoPrompt(input_with_photo)))
    print(await llm.generate(QuestionWithPhotoPrompt(input_without_photo)))


asyncio.run(main())
```