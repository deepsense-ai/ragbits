from pydantic import BaseModel
from ragbits.core.prompt import Prompt


class BasicAnswerGenInput(BaseModel):
    chunk: str
    question: str


class BasicAnswerGenPrompt(Prompt[BasicAnswerGenInput, str]):

    system_prompt = """You are an AI assistant to answer the given question in the provide evidence text.
  Do not mention any of these in the answer: "in the given text", "in the provided information", etc.
Users do not know the passage source of the answer, so it should not be mentioned in the answer.
You can find the evidence from the given text about question, and you have to write a proper answer to the given question.
If you don't know the answer just say: I don't know."""

    user_prompt = "Text:\n<|text_start|>\n {{ chunk }} \n<|text_end|>\n\nQuestion:\n {{ question }} \n\nAnswer:"