from pydantic import BaseModel

from ragbits.core.prompt import Prompt


class BasicCorpusGenerationPromptInput(BaseModel):
    """A definition of input for corpus generation task"""

    query: str


class BasicCorpusGenerationPrompt(Prompt[BasicCorpusGenerationPromptInput]):
    """A basic prompt for corpus generation"""

    system_prompt: str = (
        "You are a provider of random factoids on topic requested by a user."
        "Do not write a long essays, the response for given query should be a single sentence"
        "For each query provide only a single fact about a given topic"
        "Use as few tokens as possible"
    )
    user_prompt: str = "Provide factoids about {{ query }}"
