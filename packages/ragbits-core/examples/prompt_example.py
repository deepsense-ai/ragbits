# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ragbits-core",
# ]
# ///
from pydantic import BaseModel
from ragbits.core.prompt import Prompt


class LoremPromptInput(BaseModel):
    """
    Input format for the LoremPrompt.
    """

    theme: str
    nsfw_allowed: bool = False


class LoremPromptOutput(BaseModel):
    """
    Output format for the LoremPrompt.
    """

    text: str


class LoremPrompt(Prompt[LoremPromptInput, LoremPromptOutput]):
    """
    A prompt that generates Lorem Ipsum text.
    """

    system_prompt = """
    You are a helpful Lorem Ipsum generator. The kind of vocablurary that you use besides "Lorem Ipsum" depends
    on the theme provided by the user. Make sure it is latin and not too long. {% if not nsfw_allowed %}Also, make sure
    that the text is safe for work.{% else %}You can use any text, even if it is not safe for work.{% endif %}
    """

    user_prompt = """
     theme: {{ theme }}
    """


if __name__ == "__main__":
    lorem_prompt = LoremPrompt(LoremPromptInput(theme="animals"))
    lorem_prompt.add_few_shot("theme: business", "Lorem Ipsum biznessum dolor copy machinum yearly reportum")
    print("CHAT:")
    print(lorem_prompt.chat)
    print()
    print("OUTPUT MODEL:")
    print(lorem_prompt.output_schema())
