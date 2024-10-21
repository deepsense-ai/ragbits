import pydantic

from ragbits.core.prompt.prompt import Prompt


class _PromptInput(pydantic.BaseModel):
    query: str


class QueryRephraserPrompt(Prompt[_PromptInput, str]):
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
