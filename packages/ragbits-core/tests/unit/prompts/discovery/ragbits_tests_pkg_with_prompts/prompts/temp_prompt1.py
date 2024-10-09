from pydantic import BaseModel

from ragbits.core.prompt import Prompt


class PromptForTestInputA(BaseModel):
    """
    Input format for the LoremPrompt.
    """

    theme: str
    nsfw_allowed: bool = False
    var1: str
    var2: str
    var3: str
    var4: str


class PromptForTestOutputA(BaseModel):
    """
    Output format for the LoremPrompt.
    """

    text: str


class PromptForTestA(Prompt[PromptForTestInputA, PromptForTestOutputA]):
    system_prompt = "fake system prompt"
    user_prompt = "fake user prompt"
