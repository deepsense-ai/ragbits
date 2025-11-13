from pydantic import BaseModel
from ragbits.core.prompt import Prompt


class FinancePromptInput(BaseModel):
    """Defines the structured input schema for the finance news prompt."""

    input: str


class FinancePrompt(Prompt[FinancePromptInput]):
    """Prompt for a finance news assistant."""

    system_prompt = """
    You are a helpful financial news assistant that finds and summarises financial news.
    """

    user_prompt = """
    {{ input }}
    """
