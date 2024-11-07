# How to define and use Prompts in Ragbits

This guide will walk you through defining and using prompts in Ragbits, including configuring input and output data types, creating custom output parsers, and passing images to a prompt.

## How to Define a Prompt

### Static Prompt Without an Input Model

To define a static prompt without an input model, you can create a subclass of the `Prompt` class and provide the `user_prompt` attribute.

```python
from ragbits.core.prompt import Prompt

class StaticPrompt(Prompt):
    user_prompt = "Hello, how are you?"
```

### Extending the Prompt with an Input Model
To extend the prompt with an input model, define a Pydantic model for the input data and pass it as a generic type to the `Prompt` class.

```python
from pydantic import BaseModel
from ragbits.core.prompt import Prompt

class GreetingInput(BaseModel):
    name: str

class GreetingPrompt(Prompt[GreetingInput, str]):
    user_prompt = "Hello, {{ name }}!"
```

### How to Configure Prompt's Output Data Type
#### Configuring output as a simple type
You can configure the ouput as a simple type, such as `bool`
```python
class BooleanPrompt(Prompt[GreetingInput, bool]):
    user_prompt = "Is your name {{ name }}?"
```
#### Defining output as a Pydantic Model
You can define the output of a prompt as a Pydantic model by specifying the output type as a generic parameter.
```python
from pydantic import BaseModel

class GreetingOutput(BaseModel):
    message: str

class GreetingPrompt(Prompt[GreetingInput, GreetingOutput]):
    user_prompt = "Hello, {{ name }}!"
```

### How to Create a Custom Output Parser for a Prompt
To create a custom output parser for a prompt, define a custom data type and provide a parser function.

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

### How to Pass Images to a Prompt
