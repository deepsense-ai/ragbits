# How to define and use Prompts in Ragbits

This guide will walk you through defining and using prompts in Ragbits, including configuring input and output data types, creating custom output parsers, and passing images to a prompt.

## How to Define a Prompt

### Static Prompt Without an Input Model

To define a static prompt without an input model, you can create a subclass of the [`Prompt`](ragbits.core.prompt.Prompt) class and provide the [`user_prompt`](ragbits.core.prompt.Prompt.user_prompt) attribute.

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
To extend the prompt with an input model, define a Pydantic model for the input data and pass it as a generic type to the [`Prompt`](ragbits.core.prompt.Prompt) class. The output type defaults to string.

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
### How to configure [`Prompt`](ragbits.core.prompt.Prompt)'s output data type
#### Defining output as a Pydantic Model
You can define the output of a prompt as a Pydantic model by specifying the output type as a generic parameter. However, note that not all llm models support output schema definition. To use this feature effectively, you must set the `use_structured_output=True` flag when initializing the LLM. If this flag is not used, you will need to ensure that the JSON schema of your data model is incorporated into the prompt.

Let’s revisit the previous example, making one adjustment: this time, we will define a structured output format.

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


class OutputSchema(BaseModel):
    last: str
    previous: str


class RAGPrompt(Prompt[QueryWithContext, OutputSchema]):
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
    llm = LiteLLM(model_name="gpt-4o-2024-08-06", use_structured_output=True)
    query = "Write down names of last two world cup winners"
    context = ["Today is November 2017", "Germany won 2014 world cup", "Spain won 2010 world cup"]
    prompt = RAGPrompt(QueryWithContext(query=query, context=context))
    response = await llm.generate(prompt)
    print(response)


asyncio.run(main())
```

After succesful execution console should display:

```text
last='Germany' previous='Spain'
```
#### Configuring output as a simple type
You can configure the ouput as a simple type, such as `bool`, `int` or `float`.
In order for those parsers to execute properly you would need to force the model with the prompt that you pass
to generate raw response in a format that can be converted to numeric type (for `int` and `float`) or some finite
set of words (the example below shows exact values) that are interpreted as bool. If those conditions are not met
`ragbits.core.prompt.parsers.ResponseParsingError` would be raised

```python
import asyncio

from pydantic import BaseModel

from ragbits.core.llms.litellm import LiteLLM
from ragbits.core.prompt import Prompt
from ragbits.core.prompt.parsers import ResponseParsingError


class RoleInput(BaseModel):
    role: str


class BooleanPrompt(Prompt[RoleInput, bool]):
    user_prompt = ("Are you {{ role }}? Answer 'yes' or 'no' only."
        "Do not provide any other additional information - just a single word"
                   )

def assert_responses(boolean_prompt: BooleanPrompt) -> None:
    # all allowed values parsed to true
    for s in ["true", "1", "yes", "y", "TRUE", "YES"]:
        assert boolean_prompt.parse_response(s)
    # all allowed values parsed to false
    for s in ["false", "0", "no", "n", "FALSE", "NO"]:
        assert not boolean_prompt.parse_response(s)

async def main():
    llm = LiteLLM()
    boolean_prompt = BooleanPrompt(RoleInput(role="a human"))
    assert_responses(boolean_prompt)
    try:
        gen = await llm.generate(prompt=boolean_prompt)
    except ResponseParsingError as e:
        print(f"Failed to parse response: {e}")
    print(gen)


asyncio.run(main())
```



### How to create a custom output parser for a [`Prompt`](ragbits.core.prompt.Prompt)
The limitiations described above can be handled by creating a custom parser. The example below will show you how:

```python
import asyncio
import re
from pydantic import BaseModel

from ragbits.core.llms.litellm import LiteLLM
from ragbits.core.prompt import Prompt


class ItemInput(BaseModel):
    items: str


class IntegerPrompt(Prompt[ItemInput, int]):
    system_prompt = "Respond to user as quantitive analytics bot"
    user_prompt = "How many {{ items }}"

    @staticmethod
    def response_parser(response: str) -> int:
        print(response)
        all_integers = re.findall(r"\b\d+\b", response)
        if len(all_integers) > 0:
            return all_integers[0]
        return -1


async def main():
    llm = LiteLLM()
    prompt = IntegerPrompt(ItemInput(items="people do live in Raglandia?"))
    response = await llm.generate(prompt=prompt)
    print(response)


asyncio.run(main())
```

