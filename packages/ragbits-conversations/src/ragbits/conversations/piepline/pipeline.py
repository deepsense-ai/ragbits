from collections.abc import Sequence

from ragbits.conversations.piepline.plugins import ConversationPipelinePlugin
from ragbits.conversations.piepline.state import ConversationPipelineResult, ConversationPipelineState
from ragbits.conversations.piepline.state_to_chat import DefaultStateToChatConverter, StateToChatConverter
from ragbits.core.llms.base import LLM


class ConversationPiepline:
    """
    Class that runs a conversation pipeline with the given plugins
    """

    def __init__(
        self,
        llm: LLM,
        plugins: Sequence[ConversationPipelinePlugin] = [],
        state_to_chat: StateToChatConverter | None = None,
    ) -> None:
        self.llm = llm
        self.plugins = plugins
        self.state_to_chat = state_to_chat or DefaultStateToChatConverter()

    async def _process_state(self, state: ConversationPipelineState) -> ConversationPipelineState:
        for plugin in self.plugins:
            state = await plugin.process_state(state)
        return state

    async def _process_result(self, result: ConversationPipelineResult) -> ConversationPipelineResult:
        for plugin in reversed(self.plugins):
            result = await plugin.process_result(result)
        return result

    async def run(
        self,
        input: ConversationPipelineState | str,
    ) -> ConversationPipelineResult:
        """
        Runs the conversation pipeline with the given input.
        """
        # Create and the state to proccess it
        state = ConversationPipelineState(user_question=input) if isinstance(input, str) else input
        state = await self._process_state(state)

        # Convert the state to chat conversation
        chat = await self.state_to_chat.convert(state)

        # Create output stream from the LLM
        stream = self.llm.generate_streaming(chat)

        # Create the result and apply plugins
        result = ConversationPipelineResult(plugin_metadata=state.plugin_metadata, output_stream=stream)
        result = await self._process_result(result)

        return result
