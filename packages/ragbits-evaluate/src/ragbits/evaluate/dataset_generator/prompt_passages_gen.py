from pydantic import BaseModel
from ragbits.core.prompt import Prompt


class PassagesGenInput(BaseModel):
    question: str
    answer: str
    chunk: str


class PassagesGenPrompt(Prompt[PassagesGenInput, str]):

    system_prompt = """You are an AI tasked with retrieving passages (one or many) from the provided Chunk that that contain information needed to generate the provided Answer to the given Question.

Instructions:
1. Each Passage MUST be VERBATIM and EXACT, without any modifications
2. Please provide the response in the form of a Python list. It should begin with "[" and end with "]"
3. You MUST start your answer with "["
4. The Chunk ALWAYS contains information needed to justify the Answer
5. Each passage must be as BRIEF as possible; DO NOT RETURN FULL SENTENCES"""

    user_prompt = "Question:\n {{ question }} \nAnswer:\n {{ answer }} \nChunk:\n {{ chunk }}\n\nPassages:"