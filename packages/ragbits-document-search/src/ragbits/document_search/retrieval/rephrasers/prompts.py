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


class MultiQueryRephraserInput(BaseModel):
    """
    Represents the input data for the multi query rephraser prompt.
    """

    query: str
    n: int


class MultiQueryRephraserPrompt(Prompt[MultiQueryRephraserInput, list]):
    """
    A prompt template for generating multiple query rephrasings.
    """

    user_prompt = "{{ query }}"
    system_prompt = (
        "You are a helpful assistant that creates short rephrased versions of a given query. "
        "Your task is to generate {{ n }} different versions of the given user query to retrieve relevant documents"
        " from a vector database. They can be phrased as statements, as they will be used as a search query. "
        "By generating multiple perspectives on the user query, "
        "your goal is to help the user overcome some of the limitations of the distance-based similarity search."
        "Alternative queries should only contain information present in the original query. Do not include anything"
        " in the alternative query, you have not seen in the original version.\n\n"
        "It is VERY important you DO NOT ADD any comments or notes. Return ONLY alternative queries. "
        "Provide these alternative queries separated by newlines. "
        "DO NOT ADD any enumeration."
    )

    @staticmethod
    def _list_parser(value: str) -> list[str]:
        return value.split("\n")

    response_parser = _list_parser


def get_rephraser_prompt(prompt: str) -> type[Prompt[Any, Any]]:
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
