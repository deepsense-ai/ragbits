from collections.abc import AsyncGenerator

from ragbits.conversations.history.compressors.base import ConversationHistoryCompressor
from ragbits.conversations.history.compressors.llm import StandaloneMessageCompressor
from ragbits.conversations.piepline.state import ConversationPipelineResult, ConversationPipelineState
from ragbits.core.llms.base import LLM
from ragbits.core.pipelines.pipeline import Step
from ragbits.core.prompt.base import ChatFormat
from ragbits.document_search import DocumentSearch


class StrToStateStep(Step):
    """
    A plugin that converts a string to a conversation pipeline state.
    """

    async def run(self, input: str | ConversationPipelineState) -> ConversationPipelineState:  # noqa: PLR6301
        """
        Processes the input and returns the conversation pipeline state.
        """
        return ConversationPipelineState(user_question=input) if isinstance(input, str) else input


class DocumentSearchRAGStep(Step):
    """
    A plugin that searches for documents using RAG.
    """

    def __init__(self, document_search: DocumentSearch) -> None:
        self.document_search = document_search

    async def run(self, state: ConversationPipelineState) -> ConversationPipelineState:
        """
        Processes the conversation pipeline state and returns the updated state.
        """
        documents = await self.document_search.search(state.user_question)
        state.rag_context = [doc.text_representation for doc in documents if doc.text_representation]
        state.plugin_metadata["document_search"] = {
            "sources": [doc.document_meta.source.model_dump_json() for doc in documents],
        }

        return state


class AddHistoryStep(Step):
    """
    A plugin that adds history to the conversation pipeline state.
    """

    def __init__(self, history: ChatFormat) -> None:
        self.history = history

    async def run(self, state: ConversationPipelineState) -> ConversationPipelineState:
        """
        Processes the conversation pipeline state and returns the updated state.
        """
        state.history = self.history
        return state


class HistoryCompressionStep(Step):
    """
    A plugin that removes history from the conversation pipeline state
    and adds any nesseseaty context from history to the user question.
    """

    def __init__(self, llm: LLM, compressor: ConversationHistoryCompressor | None = None) -> None:
        self.compressor = compressor or StandaloneMessageCompressor(llm)

    async def run(self, state: ConversationPipelineState) -> ConversationPipelineState:
        """
        Processes the conversation pipeline state and returns the updated state.
        """
        full_history = state.history + [{"role": "user", "content": state.user_question}]
        state.user_question = await self.compressor.compress(full_history)
        state.history = []
        state.plugin_metadata["history_compression"] = {
            "compressed_question": state.user_question,
        }
        return state


class CensorCreamStep(Step):
    """
    A plugin that censors the word "cream" from the conversation pipeline state.
    """

    async def run(self, result: ConversationPipelineResult) -> ConversationPipelineResult:
        """
        Processes the conversation pipeline result and returns the updated result.
        """
        result.output_stream = self._process_output_stream(result.output_stream)
        return result

    async def _process_output_stream(self, stream: AsyncGenerator[str, None]) -> AsyncGenerator[str, None]:  # noqa: PLR6301
        """
        Processes the output stream and returns the updated stream.
        """
        async for item in stream:
            yield item.replace("cream", "*****")
