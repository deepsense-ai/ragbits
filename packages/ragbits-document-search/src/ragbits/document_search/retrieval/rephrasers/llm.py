from typing import Optional

from ragbits.core.llms import get_llm
from ragbits.core.llms.base import LLM, LLMOptions
from ragbits.core.prompt import Prompt
from ragbits.document_search.retrieval.rephrasers.base import QueryRephraser
from ragbits.document_search.retrieval.rephrasers.prompt_query_rephraser import QueryRephraserPrompt, _PromptInput


class LLMQueryRephraser(QueryRephraser):
    """A rephraser class that uses a LLM to rephrase queries."""

    def __init__(self, llm: LLM):
        """
        Initialize the LLMQueryRephraser with a LLM.

        Args:
            llm: A LLM instance to handle query rephrasing.
        """

        self._llm = llm

    async def rephrase(
        self, query: Optional[str] = None, prompt: Optional[Prompt] = None, options: Optional[LLMOptions] = None
    ) -> list[str]:
        """
        Rephrase a given query using the LLM.

        Args:
            query: The query to be rephrased. If not provided, a custom prompt must be given.
            prompt: A prompt object defining how the rephrasing should be done.
                    If not provided, the default `QueryRephraserPrompt` is used, along with the provided query.
            options: Optional settings for the LLM to control generation behavior.

        Returns:
            A list containing the rephrased query.

        Raises:
            ValueError: If both `query` and `prompt` are None.
        """

        if query is None and prompt is None:
            raise ValueError("Either `query` or `prompt` must be provided.")

        if prompt is not None:
            response = await self._llm.generate(prompt, options=options)

        else:
            assert isinstance(query, str)
            response = await self._llm.generate(QueryRephraserPrompt(_PromptInput(query=query)), options=options)

        return [response]

    @classmethod
    def from_config(cls, config: dict) -> "LLMQueryRephraser":
        """
        Create an instance of `LLMQueryRephraser` from a configuration dictionary.

        Args:
            config: A dictionary containing configuration settings for the rephraser.

        Returns:
            An instance of the rephraser class initialized with the provided configuration.
        """

        llm = get_llm(config["llm"])

        return cls(llm=llm)
