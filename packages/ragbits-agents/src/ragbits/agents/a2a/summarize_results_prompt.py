from pydantic import BaseModel

from ragbits.core.prompt import Prompt


class SummarizeAgentResultsInput(BaseModel):
    """
    Input model for SummarizeAgentResultsPrompt.
    """

    message: str
    agent_results: list


class SummarizeAgentResultsPrompt(Prompt[SummarizeAgentResultsInput]):
    """
    Prompt template for summarizing results from multiple agents.

    The system prompt instructs to combine multiple tool outputs into
    a concise, user-friendly reply based on the original user message.
    """

    system_prompt = """
You are a smart assistant that takes multiple tool outputs and combines them into a response to the user message.

Below are the results returned by specialized tools:
{% for result in agent_results %}
- {{ result }}
{% endfor %}

Please write a concise, user-friendly reply to the user message based on these results.
"""
    user_prompt = "{{ message }}"
