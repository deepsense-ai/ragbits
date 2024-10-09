from abc import ABC

from pydantic import BaseModel

from ragbits.core.prompt import Prompt


class PromptForTestInput(BaseModel):
    """
    Input format for the LoremPrompt.
    """

    theme: str
    nsfw_allowed: bool = False
    var1: str
    var2: str
    var3: str
    var4: str


class PromptForTestOutput(BaseModel):
    """
    Output format for the LoremPrompt.
    """

    text: str


class PromptForTest(Prompt[PromptForTestInput, PromptForTestOutput]):
    system_prompt = "fake system prompt"
    user_prompt = "fake user prompt"


class PromptForTestInput2(BaseModel):
    """
    Input format for the LoremPrompt.
    """

    theme: str


class PromptForTestOutput2(BaseModel):
    """
    Output format for the LoremPrompt.
    """

    text: str


class PromptForTest2(Prompt[PromptForTestInput2, PromptForTestOutput2]):
    system_prompt = "fake system prompt2"
    user_prompt = "fake user prompt2"


class MyBasePrompt(Prompt, ABC):
    system_prompt = "my base system prompt"
    user_prompt = "temp user prompt"


class MyPromptWithBase(MyBasePrompt):
    user_prompt = "custom user prompt"


class PromptWithoutInput(Prompt):
    system_prompt = "fake system prompt without typing"
    user_prompt = "fake user prompt without typing"
