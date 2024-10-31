from pydantic import BaseModel
from ragbits.core.prompt import Prompt


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