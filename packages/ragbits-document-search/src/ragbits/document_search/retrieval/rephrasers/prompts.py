import sys
from typing import Any

from pydantic import BaseModel

from ragbits.core.prompt.prompt import Prompt
from ragbits.core.utils.config_handling import import_by_path

module = sys.modules[__name__]


class QueryRephraserInput(BaseModel):
    """
    Input data for the query rephraser prompt.
    """

    query: str


class QueryRephraserPrompt(Prompt[QueryRephraserInput, str]):
    """
    A prompt class for generating a rephrased version of a user's query using a LLM.
    """

    user_prompt = "{{ query }}"
    system_prompt = (
        "You are an expert in query rephrasing and clarity improvement. "
        "Your task is to return a single paraphrased version of a user's query, "
        "correcting any typos, handling abbreviations and improving clarity. "
        "Focus on making the query more precise and readable while keeping its original intent.\n\n"
        "Just return the rephrased query. No additional explanations are needed."
    )


def get_rephraser_prompt(prompt: str) -> type[Prompt[QueryRephraserInput, Any]]:
    """
    Initializes and returns a QueryRephraser object based on the provided configuration.

    Args:
        prompt: The prompt class to use for rephrasing queries.

    Returns:
        An instance of the specified QueryRephraser class, initialized with the provided config
        (if any) or default arguments.

    Raises:
        ValueError: If the prompt class is not a subclass of `Prompt`.
    """
    prompt_cls = import_by_path(prompt, module)

    if not issubclass(prompt_cls, Prompt):
        raise ValueError(f"Invalid rephraser prompt class: {prompt_cls}")

    return prompt_cls
