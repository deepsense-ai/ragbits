# Quickstart 1: Working with Prompts and LLMs

In this Quickstart guide, you will learn how to define a dynamic prompt in Ragbits and how to use such a prompt with Large Language Models.

## Installing Ragbits

To install Ragbits, run the following command in your terminal:

```bash
pip install ragbits
```

This command will install all the popular Ragbits packages.

## Defining a Static Prompt
The most standard way to define a prompt in Ragbits is to create a class that inherits from the `Prompt` class and configure it by setting values for appropriate properties. Here is an example of a simple prompt that asks the model to write a song about Ragbits:

```python
from ragbits.core.prompt import Prompt

class SongPrompt(Prompt):
    user_prompt = """
        Write a song about a Python library called Ragbits.
    """
```

In this case, all you had to do was set the `user_prompt` property to the desired prompt. That's it! This prompt can now be used anytime you want to pass a prompt to Ragbits.

Next, we'll learn how to make this prompt more dynamic (e.g., by adding placeholders for user inputs). But first, let's see how to use this prompt with a Large Language Model.

## Testing the Prompt from the CLI
Even at this stage, you can test the prompt using the built-in `ragbits` CLI tool. To do this, you need to run the following command in your terminal:

```bash
ragbits prompts exec path.within.your.project:SongPrompt
```

Where `path.within.your.project` is the path to the Python module where the prompt is defined. In the simplest case, when you are in the same directory as the file, it will be the name of the file without the `.py` extension. For example, if the prompt is defined in a file named `song_prompt.py`, you would run:

```bash
ragbits prompts exec song_prompt:SongPrompt
```

This command will send the prompt to the default Large Language Model and display the generated response in the terminal.

!!! note
    If there is no default LLM configured for your project, Ragbits will use OpenAI's gpt-3.5-turbo. Ensure that the `OPENAI_API_KEY` environment variable is set and contains your OpenAI API key.

    Alternatively, you can use your custom LLM factory (a function that creates an instance of [Ragbits's LLM class][ragbits.core.llms.LLM]) by specifying the path to the factory function using the `--llm-factory` option with the `ragbits prompts exec` command.

    <!-- TODO: link to the how-to on configuring default LLMs in pyproject.toml -->

## Using the Prompt in Python Code
To use the defined prompt with a Large Language Model in Python, you need to create an instance of the model and pass the prompt to it. For instance:

```python
from ragbits.core.llms.litellm import LiteLLM

llm = LiteLLM("gpt-4")
response = await llm.generate(prompt)
print(f"Generated song: {response}")
```

In this code snippet, we first created an instance of the `LiteLLM` class and configured it to use OpenAI's `gpt-4` model. We then generated a response by passing the prompt to the model. As a result, the model will generate a song about Ragbits based on the provided prompt.

## Making the Prompt Dynamic
You can make the prompt dynamic by declaring a Pydantic model that serves as the prompt's input schema (i.e., declares the shape of the data that you will be able to use in the prompt). Here's an example:

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

## Testing the Dynamic Prompt in CLI
Besides using the dynamic prompt in Python, you can still test it using the `ragbits` CLI tool. The only difference is that now you need to provide the values for the placeholders in the prompt in JSON format. Here's an example:

```bash
ragbits prompts exec song_prompt:SongPrompt --payload '{"subject": "unicorns", "age_group": 12, "genre": "pop"}'
```

Remember to change `song_prompt` to the name of the module where the prompt is defined and adjust the values of the placeholders to your liking.

!!! tip
    Ragbits also comes with a built-in GUI tool called Prompts Lab that allows you to manage and interact with prompts in a more user-friendly way. To learn more about using Prompts Lab, see the how-to article [How to Manage Prompts using GUI with Prompts Lab](../how-to/core/prompts_lab.md).

## Conclusion
You now know how to define a prompt in Ragbits and how to use it with Large Language Models. You've also learned to make the prompt dynamic by using Pydantic models and the Jinja2 templating language. To learn more about defining prompts, such as configuring the desired output format, refer to the how-to article [How to define and use Prompts in Ragbits](../how-to/core/use_prompting.md).

<!-- TODO: Add a link to the how-to articles on using images in prompts and on defining custom prompt sources -->

## Next Step
In the next Quickstart guide, you will learn how to use Ragbits's Document Search capabilities to retrieve relevant documents for your prompts: [Quickstart 2: Adding RAG Capabilities](quickstart2_rag.md).