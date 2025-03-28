from ragbits.conversations.piepline.state import ConversationPipelineState
from ragbits.core.pipelines.pipeline import Step
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


class DefaultStateToChatStep(Step):
    """
    Default implementation of the state to chat converter.
    """

    def __init__(self, prompt_cls: type[Prompt[ConversationPipelineState]] = DefaultConversationPrompt):
        self.prompt_cls = prompt_cls

    async def run(self, state: ConversationPipelineState) -> ChatFormat:
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
