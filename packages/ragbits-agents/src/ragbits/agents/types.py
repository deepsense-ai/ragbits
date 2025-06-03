from typing import Any, TypeVar

from pydantic import BaseModel

from ragbits.agents._main import Agent
from ragbits.core.llms.base import LLMClientOptionsT

QuestionAnswerPromptInputT = TypeVar("QuestionAnswerPromptInputT", bound="QuestionAnswerPromptInput")
QuestionAnswerPromptOutputT = TypeVar("QuestionAnswerPromptOutputT", bound="QuestionAnswerPromptOutput | str")

QuestionAnswerAgent = Agent[LLMClientOptionsT, QuestionAnswerPromptInputT, QuestionAnswerPromptOutputT]


class QuestionAnswerPromptInput(BaseModel):
    """
    Input for the question answer agent.
    """

    question: str
    """The question to answer."""
    context: Any | None = None
    """The context to answer the question."""


class QuestionAnswerPromptOutput(BaseModel):
    """
    Output for the question answer agent.
    """

    answer: str
    """The answer to the question."""
