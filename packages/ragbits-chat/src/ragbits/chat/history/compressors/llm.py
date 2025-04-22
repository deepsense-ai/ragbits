from pydantic import BaseModel

from ragbits.chat.history.compressors import ConversationHistoryCompressor
from ragbits.core.llms.base import LLM
from ragbits.core.prompt import ChatFormat, Prompt


class LastMessageAndHistory(BaseModel):
    """
    A class representing the last message and the history of messages.
    """

    last_message: str
    history: list[str]


class StandaloneMessageCompressorPrompt(Prompt[LastMessageAndHistory, str]):
    """
    A prompt for recontextualizing the last message in the history.
    """

    system_prompt = """
    Given a new message and a history of the conversation, create a standalone version of the message.
    If the message references any context from history, it should be added to the message itself.
    Return only the recontextualized message.
    Do NOT return the history, do NOT answer the question, and do NOT add context irrelevant to the message.
    """

    user_prompt = """
    Message:
    {{ last_message }}

    History:
    {% for message in history %}
    * {{ message }}
    {% endfor %}
    """


class StandaloneMessageCompressor(ConversationHistoryCompressor):
    """
    A compressor that uses LLM to recontextualize the last message in the history,
    i.e. create a standalone version of the message that includes necessary context.
    """

    def __init__(self, llm: LLM, history_len: int = 5, prompt: type[Prompt[LastMessageAndHistory, str]] | None = None):
        """
        Initialize the StandaloneMessageCompressor compressor with a LLM.

        Args:
            llm: A LLM instance to handle recontextualizing the last message.
            history_len: The number of previous messages to include in the history.
            prompt: The prompt to use for recontextualizing the last message.
        """
        self._llm = llm
        self._history_len = history_len
        self._prompt = prompt or StandaloneMessageCompressorPrompt

    async def compress(self, conversation: ChatFormat) -> str:
        """
        Contextualize the last message in the conversation history.

        Args:
            conversation: List of dicts with "role" and "content" keys, representing the chat history so far.
                The most recent message should be from the user.
        """
        if len(conversation) == 0:
            raise ValueError("Conversation history is empty.")

        last_message = conversation[-1]
        if last_message["role"] != "user":
            raise ValueError("StandaloneMessageCompressor expects the last message to be from the user.")

        # Only include "user" and "assistant" messages in the history
        other_messages = [message for message in conversation[:-1] if message["role"] in ["user", "assistant"]]

        if not other_messages:
            # No history to use for recontextualization, simply return the user message
            return last_message["content"]

        history = [f"{message['role']}: {message['content']}" for message in other_messages[-self._history_len :]]

        input_data = LastMessageAndHistory(last_message=last_message["content"], history=history)
        prompt = self._prompt(input_data)
        response = await self._llm.generate(prompt)
        return response
