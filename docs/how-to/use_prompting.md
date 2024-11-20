# How to define and use Prompts in Ragbits

This guide will walk you through defining and using prompts in Ragbits, including configuring input and output data types, creating custom output parsers, and passing images to a prompt.

## How to Define a Prompt

### Static Prompt Without an Input Model

To define a static prompt without an input model, you can create a subclass of the `Prompt` class and provide the `user_prompt` attribute.

```python
from ragbits.core.prompt import Prompt


class JokePrompt(Prompt):
    """
    A prompt that generates jokes.
    """

    system_prompt = """
    You are a joke generator. The jokes you generate should be funny and not offensive.
    """

    user_prompt = """Tell me a joke."""
```
Passing the prompt to a model is as simple as:
```python
import asyncio
from ragbits.core.llms.litellm import LiteLLM

async def main():
    llm = LiteLLM("gpt-4o-2024-08-06", use_structured_output=True)
    static_prompt = JokePrompt()
    print(await llm.generate(static_prompt))

asyncio.run(main())
```

### Extending the Prompt with an Input Model
To extend the prompt with an input model, define a Pydantic model for the input data and pass it as a generic type to the `Prompt` class. The output type defaults to string.

Let's use a RAG example as a case study:

```python
import asyncio
from pydantic import BaseModel

from ragbits.core.prompt import Prompt
from ragbits.core.llms.litellm import LiteLLM


class QueryWithContext(BaseModel):
    """
    Input format for the QueryWithContext.
    """

    query: str
    context: list[str]


class RAGPrompt(Prompt[QueryWithContext]):
    """
    A simple prompt for RAG system.
    """

    system_prompt = """
    You are a helpful assistant. Answer the QUESTION that will be provided using CONTEXT.
    If in the given CONTEXT there is not enough information refuse to answer.
    """

    user_prompt = """
    QUESTION:
    {{ query }}

    CONTEXT:
    {% for item in context %}
        {{ item }}
    {% endfor %}
    """


async def main():
    llm = LiteLLM()
    query = "Write down names of last two world cup winners"
    context = ["Today is November 2017", "Germany won 2014 world cup", "Spain won 2010 world cup"]
    prompt = RAGPrompt(QueryWithContext(query=query, context=context))
    response = await llm.generate(prompt)
    print(response)


asyncio.run(main())
```

After succesful execution console should something like:

```text
The last two World Cup winners as of November 2017 are Germany (2014) and Spain (2010).
```
### How to configure `Prompt`'s output data type
#### Defining output as a Pydantic Model
You can define the output of a prompt as a Pydantic model by specifying the output type as a generic parameter.
```python
from pydantic import BaseModel

from ragbits.core.prompt import Prompt


class QueryWithContext(BaseModel):
    """
    Input format for the QueryWithContext.
    """

    query: str
    context: list[str]


class ChatAnswer(BaseModel):
    """
    Output format for the ChatAnswer.
    """

    answer: str


class RAGPrompt(Prompt[QueryWithContext, ChatAnswer]):
    """
    A simple prompt for RAG system.
    """

    system_prompt = """
    You are a helpful assistant. Answer the QUESTION that will be provided using CONTEXT.
    If in the given CONTEXT there is not enough information refuse to answer.
    """

    user_prompt = """
    QUESTION:
    {{ query }}

    CONTEXT:
    {% for item in context %}
        {{ item }}
    {% endfor %}
    """

...

prompt = RAGPrompt(QueryWithContext(query=message, context=[i.get_text_representation() for i in results]))
response = await self._llm.generate(prompt)
print(response.answer)
...
```
#### Configuring output as a simple type
You can configure the ouput as a simple type, such as `bool`
```python
from pydantic import BaseModel

from ragbits.core.prompt import Prompt


class RoleInput(BaseModel):
    role: str


class BooleanPrompt(Prompt[RoleInput, bool]):
    user_prompt = "Are you {{ role }}? Answer 'yes' or 'no' only."


boolean_prompt = BooleanPrompt(RoleInput(role = "an AI Assistant"))
assert boolean_prompt.parse_response("true") is True
```
Please note that an actual response from LLM is going to raise `ResponseParsingError`. This is because the response is not natively parsable to boolean:
```python
llm = LiteLLM("gpt-4o-2024-08-06", use_structured_output=True)
print(await llm.generate(boolean_prompt))
```
```
ragbits.core.prompt.parsers.ResponseParsingError: Could not parse 'yes, i am an ai assistant designed to help with a wide range of inquiries and tasks. how can i assist you today?' as a boolean
```
Although it can be fixed with a proper prompt, please see how to create a custom output parser for a `Prompt` below.

### How to create a custom output parser for a `Prompt`
To create a custom output parser for a prompt, define a custom data type and provide a parser function.

```python
from pydantic import BaseModel

from ragbits.core.prompt import Prompt
from ragbits.core.prompt.parsers import ResponseParsingError


class RoleInput(BaseModel):
    role: str


class BooleanPrompt(Prompt[RoleInput, bool]):
    user_prompt = "Are you {{ role }}? (yes/no)"

    @staticmethod
    def response_parser(response: str) -> bool:
        print("resp",response)
        if "yes" in response.lower():
            return True
        elif "no" in response.lower():
            return False
        else:
            raise ResponseParsingError("Response is not a valid boolean value.")
```

Another example of custom parser for handling empty responses.
```python
from ragbits.core.prompt import Prompt
from ragbits.core.prompt.parsers import ResponseParsingError

class CustomOutput:
    def __init__(self, value: str):
        self.value = value

class CustomPrompt(Prompt[GreetingInput, CustomOutput]):
    user_prompt = "Hello, {{ name }}!"

    @staticmethod
    def response_parser(response: str) -> CustomOutput:
        if not response:
            raise ResponseParsingError("Response is empty")
        return CustomOutput(response)
```
