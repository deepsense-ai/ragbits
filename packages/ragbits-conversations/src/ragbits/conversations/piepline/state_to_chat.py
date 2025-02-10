import abc

from ragbits.conversations.piepline.state import ConversationPipelineState
from ragbits.core.prompt.prompt import ChatFormat, Prompt


class DefaultConversationPrompt(Prompt[ConversationPipelineState]):
    """
    A prompt that generates Lorem Ipsum text.
    """

    system_prompt = """
    You are a helpful conversational agent.
    You will get user's message {% if rag_context %}and additional context{% endif %} and you should respond
    to the message using the context provided.
    """

    user_prompt = """
     message: {{ user_question }}

    {% if rag_context %}
    ---
    Additional context:
    {% for context in rag_context %}
    - {{ context }}
    {% endfor %}
    {% endif %}
    """


class StateToChatConverter(abc.ABC):
    """
    Abstract class for state to chat converters.
    """

    @abc.abstractmethod
    async def convert(self, state: ConversationPipelineState) -> ChatFormat:
        """
        Function that takes the state of the conversation pipeline and returns the chat format for the LLM.
        """


class DefaultStateToChatConverter(StateToChatConverter):
    """
    Default implementation of the state to chat converter.
    """

    def __init__(self, prompt_cls: type[Prompt[ConversationPipelineState]] = DefaultConversationPrompt):
        self.prompt_cls = prompt_cls

    async def convert(self, state: ConversationPipelineState) -> ChatFormat:
        """
        Converts the state to chat format.
        """
        prompt = self.prompt_cls(state)
        chat = prompt.chat

        chat_with_history = [
            *chat[:-1],
            *state.history,
            chat[-1],
        ]

        return chat_with_history
