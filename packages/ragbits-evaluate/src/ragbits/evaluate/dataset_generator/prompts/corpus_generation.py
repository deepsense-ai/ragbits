from pydantic import BaseModel
from ragbits.core.prompt import Prompt


class BasicCorpusGenerationPromptInput(BaseModel):
    query: str


class BasicCorpusGenerationPrompt(Prompt[BasicCorpusGenerationPromptInput]):
    system_prompt: str = "You are a provider of random factoids on topic requested by a user. Use very few tokens and sentence equivalents"
    user_prompt: str = "Provide factoids about {{ query }}"

