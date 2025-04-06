from collections.abc import Sequence

from ragbits.conversations.piepline.state import ConversationPipelineResult, ConversationPipelineState
from ragbits.conversations.piepline.state_to_chat import DefaultStateToChatStep
from ragbits.conversations.piepline.steps import StrToStateStep
from ragbits.core.llms.base import LLM
from ragbits.core.pipelines.pipeline import Pipeline, Step
from ragbits.core.prompt.prompt import ChatFormat


class RunLLMStep(Step):
    """
    A plugin that runs the LLM on the conversation pipeline state.
    """

    def __init__(self, llm: LLM, state_to_chat: Step[ConversationPipelineState, ChatFormat]) -> None:
        self.llm = llm
        self.state_to_chat = state_to_chat

    async def run(self, state: ConversationPipelineState) -> ConversationPipelineResult:
        """
        Processes the conversation pipeline state and returns the updated result.
        """
        chat = await self.state_to_chat.run(state)
        stream = self.llm.generate_streaming(chat)
        return ConversationPipelineResult(plugin_metadata=state.plugin_metadata, output_stream=stream)


class ConversationPiepline(Step):
    """
    Class that runs a conversation pipeline with the given plugins
    """

    def __init__(
        self,
        llm: LLM,
        preprocessors: Sequence[Step[ConversationPipelineState, ConversationPipelineState]] = [],
        postprocessors: Sequence[Step[ConversationPipelineResult, ConversationPipelineResult]] = [],
        state_to_chat: Step[ConversationPipelineState, ChatFormat] | None = None,
    ) -> None:
        self.llm = llm
        self.preprocessors = preprocessors
        self.state_to_chat = state_to_chat or DefaultStateToChatStep()
        self.postprocessors = postprocessors

    async def _process_state(self, state: ConversationPipelineState) -> ConversationPipelineState:
        for preprocess in self.preprocessors:
            state = await preprocess.run(state)
        return state

    async def _process_result(self, result: ConversationPipelineResult) -> ConversationPipelineResult:
        for postprocess in self.postprocessors:
            result = await postprocess.run(result)
        return result

    async def run(
        self,
        input: ConversationPipelineState | str,
    ) -> ConversationPipelineResult:
        """
        Runs the conversation pipeline with the given input.
        """
        pipeline = Pipeline[str | ConversationPipelineState, ConversationPipelineResult](
            StrToStateStep(),
            *self.preprocessors,
            RunLLMStep(self.llm, self.state_to_chat),
            *self.postprocessors,
        )

        return await pipeline.run(input)
