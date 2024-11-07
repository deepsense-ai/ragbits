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


class PassagesGenInput(BaseModel):
    question: str
    basic_answer: str
    chunk: str


class PassagesGenPrompt(Prompt[PassagesGenInput, str]):
    system_prompt = """You are an AI tasked with retrieving passages (one or many) from the provided Chunk that that contain information needed to generate the provided Answer to the given Question.

Instructions:
1. Each Passage MUST be VERBATIM and EXACT, without any modifications
2. Please provide the response in the form of a Python list. It should begin with "[" and end with "]"
3. You MUST start your answer with "["
4. The Chunk ALWAYS contains information needed to justify the Answer
5. Each passage must be as BRIEF as possible; DO NOT RETURN FULL SENTENCES"""

    user_prompt = "Question:\n {{ question }} \nAnswer:\n {{ basic_answer }} \nChunk:\n {{ chunk }}\n\nPassages:"


class QueryGenInput(BaseModel):
    chunk: str


class QueryGenPrompt(Prompt[QueryGenInput, str]):
    system_prompt = """You're an AI tasked to convert Text into a factoid question.
Factoid questions are those seeking brief, factual information that can be easily verified. They typically require a yes or no answer or a brief explanation and often inquire about specific details such as dates, names, places, or events.

Examples of factoid questions include:

- What is the incoming shipment report?
- What angle should I set my ladder at?
- What documents do I need to be a proof of transaction?

Instructions:
1. Questions MUST BE extracted from given Text
2. Questions MUST BE as SHORT a possible
3. Questions should be as detailed as possible from Text
4. Create questions that ask about factual information from the Text
5. Only return ONE question
6. Frame questions in a first-person, INFROMAL style, as if the employee is seeking advice or clarification while working
7. Do not mention any of these in the questions: "in the given text", "in the provided information", etc.
Users do not know the passage source of the question, so it should not be mentioned in the question."""

    user_prompt = "Text: {{ chunk }}\n\nGenerated Question from the Text:\n"
