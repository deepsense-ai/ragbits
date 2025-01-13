from pydantic import BaseModel

from ragbits.core.prompt import Prompt


class BasicAnswerGenInput(BaseModel):
    """An input definition for basic answer generation task"""

    chunk: str
    question: str


class BasicAnswerGenPrompt(Prompt[BasicAnswerGenInput, str]):
    """A prompt clas for basic answers generation"""

    system_prompt: str = (
        "You are an AI assistant to answer the given question in the provided "
        "evidence text. Do not mention any of these in the answer: 'in the "
        "given text', 'in the provided information', etc. Users do not know "
        "the passage source of the answer, so it should not be mentioned in "
        "the answer. You can find the evidence from the given text about the "
        "question, and you have to write a proper answer to the given question. "
        "If you don't know the answer just say: I don't know."
    )

    user_prompt: str = "Text:\n<|text_start|>\n {{ chunk }} \n<|text_end|>\n\nQuestion:\n {{ question }} \n\nAnswer:"


class PassagesGenInput(BaseModel):
    """An input definition to passage generation prompt"""

    question: str
    basic_answer: str
    chunk: str


class PassagesGenPrompt(Prompt[PassagesGenInput, str]):
    """A prompt class for passages generation"""

    system_prompt: str = (
        "You are an AI tasked with retrieving passages (one or many) from the "
        "provided Chunk that contain information needed to generate the "
        "provided Answer to the given Question.\n\nInstructions:\n1. Each "
        "Passage MUST be VERBATIM and EXACT, without any modifications\n2. "
        "Please provide the response in the form of a Python list. It should "
        "begin with '[' and end with ']'\n3. You MUST start your answer with "
        "'['\n4. The Chunk ALWAYS contains information needed to justify the "
        "Answer\n5. Each passage must be as BRIEF as possible; DO NOT RETURN "
        "FULL SENTENCES"
    )

    user_prompt: str = "Question:\n {{ question }} \nAnswer:\n {{ basic_answer }} \nChunk:\n {{ chunk }}\n\nPassages:"


class QueryGenInput(BaseModel):
    """An input definition for query generation prompt"""

    chunk: str


class QueryGenPrompt(Prompt[QueryGenInput, str]):
    """A prompt class for query generation"""

    system_prompt: str = (
        "You're an AI tasked to convert Text into a factoid question. Factoid "
        "questions are those seeking brief, factual information that can be "
        "easily verified. They typically require a yes or no answer or a brief "
        "explanation and often inquire about specific details such as dates, "
        "names, places, or events.\n\nExamples of factoid questions include:\n"
        "- What is the incoming shipment report?\n- What angle should I set my "
        "ladder at?\n- What documents do I need to be a proof of transaction?\n\n"
        "Instructions:\n1. Questions MUST BE extracted from given Text\n2. "
        "Questions MUST BE as SHORT as possible\n3. Questions should be as "
        "detailed as possible from Text\n4. Create questions that ask about "
        "factual information from the Text\n5. Only return ONE question\n6. "
        "Frame questions in a first-person, INFORMAL style, as if the employee "
        "is seeking advice or clarification while working\n7. Do not mention any "
        "of these in the questions: 'in the given text', 'in the provided "
        "information', etc. Users do not know the passage source of the question, "
        "so it should not be mentioned in the question."
    )

    user_prompt: str = "Text: {{ chunk }}\n\nGenerated Question from the Text:\n"
