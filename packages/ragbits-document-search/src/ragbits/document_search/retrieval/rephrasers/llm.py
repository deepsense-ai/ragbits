from typing import Optional

from ragbits.core.llms import get_llm
from ragbits.core.llms.base import LLM, LLMOptions
from ragbits.core.utils.config_handling import get_cls_from_config
from ragbits.document_search.retrieval import rephrasers
from ragbits.document_search.retrieval.rephrasers.base import QueryRephraser
from ragbits.document_search.retrieval.rephrasers.prompt_query_rephraser import QueryRephraserPrompt, _PromptInput


class LLMQueryRephraser(QueryRephraser):
    """A rephraser class that uses a LLM to rephrase queries."""

    def __init__(self, llm: LLM, prompt: Optional[QueryRephraserPrompt] = None):
        """
        Initialize the LLMQueryRephraser with a LLM and an optional prompt.

        Args:
            llm: A LLM instance to handle query rephrasing.
            prompt: A prompt defining how the rephrasing should be done.
                If not provided, the default `QueryRephraserPrompt` is used.
        """

        self._prompt = prompt or QueryRephraserPrompt
        self._llm = llm

    async def rephrase(self, query: str, options: Optional[LLMOptions] = None) -> list[str]:
        """
        Rephrase a given query using the LLM.

        Args:
            query: The query to be rephrased.
            options: OptionaL LLM options to fine-tune the generation behavior.

        Returns:
            A list containing the rephrased query.
        """

        prompt = QueryRephraserPrompt(_PromptInput(query=query))
        response = await self._llm.generate(prompt, options=options)

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

        prompt_config = config.get("prompt")

        if prompt_config:
            prompt = get_cls_from_config(prompt_config["type"], rephrasers)
            return cls(llm=llm, prompt=prompt)

        return cls(llm=llm)
