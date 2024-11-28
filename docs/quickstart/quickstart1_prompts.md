# Quickstart 1: Working with Prompts and LLMs

In this Quickstart guide, you will learn how to define a dynamic prompt in Ragbits and how to use such a prompt with Large Language Models.

## Defining a Static Prompt
The most standard way to define a prompt in Ragbits is to create a class that inherits from the `Prompt` class and configure it by setting values for appropriate properties. Here is an example of a simple prompt that asks the model to write a song about Ragbits:

```python
from ragbits.core.prompt import Prompt

class JokePrompt(Prompt):
    user_prompt = """
        Write a song about a Python library called Ragbits.
    """
```

In this case, all you had to do was to set the `user_prompt` property to the desired prompt. That's it! This prompt can now be used anytime you want to pass Ragbits a prompt to use.

Next, we'll learn how to make this prompt more dynamic (e.g., by adding placeholders for user inputs). But first, let's see how to use this prompt with a Large Language Model.

## Passing the Prompt to a Large Language Model
To use the defined prompt with a Large Language Model, you need to create an instance of the model and pass the prompt to it. For instance:

```python
from ragbits.core.llms.litellm import LiteLLM

llm = LiteLLM("gpt-4")
response = await llm.generate(prompt)
print(f"Generated song: {response}")
```

In this code snippet, we first created an instance of the `LiteLLM` class and configured it to use the OpenAI's `gpt-4` model. We then generated a response by passing the prompt to the model. As a result, the model will generate a song about Ragbits based on the provided prompt.

## Making the Prompt Dynamic
You could make the prompt dynamic by declaring a Pydantic model that serves as the prompt's input schema (i.e., declares the shape of the data that you will be able to use in the prompt). Here's an example:

```python
from pydantic import BaseModel

class SongIdea(BaseModel):
    subject: str
    age_group: int
    genre: str
```

The defined `SongIdea` model describes the desired song - its subject, the target age group, and the genre. This model can now be used to create a dynamic prompt:

```python
class SongPrompt(Prompt[SongIdea]):
    user_prompt = """
        Write a song about a {{subject}} for {{age_group}} years old {{genre}} fans.
    """
```

In addition to using placeholders in the prompt, you can also employ the robust features of the [Jinja2](https://jinja.palletsprojects.com/) templating language to create more intricate prompts. Here's an example that incorporates a condition based on the input:

```python
class SongPrompt(Prompt[SongIdea]):
    system_prompt = """
        You are a professional songwriter.
        {% if age_group < 18 %}
            You only use language that is appropriate for children.
        {% endif %}
    """

    user_prompt = """
        Write a song about a {{subject}} for {{age_group}} years old {{genre}} fans.
    """
```

This example illustrates how to set a system prompt and use conditional statements in the prompt.

## Conclusion
You now know how to define a prompt in Ragbits and how to use it with Large Language Models. You've also learned to make the prompt dynamic by using Pydantic models and the Jinja2 templating language. To learn more about defining prompts, such as configuring the desired output format, refer to the how-to article [How to define and use Prompts in Ragbits](../how-to/use_prompting.md).

<!-- TODO: Add a link to the how-to articles on using images in prompts and on defining custom prompt sources -->

## Next Step
In the next Quickstart guide, you will learn how to use the `ragbits` CLI to manage the prompts that you've defined in your project: [Quickstart 2: Working with prompts from the command line](quickstart2_cli.md).