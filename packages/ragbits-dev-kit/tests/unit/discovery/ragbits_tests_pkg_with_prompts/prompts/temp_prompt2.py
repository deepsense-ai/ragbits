from pydantic import BaseModel

from ragbits.core.prompt import Prompt


class PromptForTestInputB(BaseModel):
    """
    Input format for the LoremPrompt.
    """

    theme: str
    nsfw_allowed: bool = False
    var1: str
    var2: str
    var3: str
    var4: str


class PromptForTestOutputB(BaseModel):
    """
    Output format for the LoremPrompt.
    """

    text: str


class PromptForTestB(Prompt[PromptForTestInputB, PromptForTestOutputB]):
    system_prompt = "fake system prompt"
    user_prompt = "fake user prompt"
