from typing import Optional

from ragbits.core.llms import get_llm
from ragbits.core.llms.base import LLM, LLMOptions
from ragbits.core.prompt import Prompt
from ragbits.core.utils.config_handling import get_cls_from_config
from ragbits.document_search.retrieval import rephrasers
from ragbits.document_search.retrieval.rephrasers.base import QueryRephraser
from ragbits.document_search.retrieval.rephrasers.prompt_query_rephraser import QueryRephraserPrompt


class LLMQueryRephraser(QueryRephraser):
    """A rephraser class that uses a LLM to rephrase queries."""

    def __init__(self, llm: LLM, prompt_strategy: Optional[type[Prompt]] = None):
        """
        Initialize the LLMQueryRephraser with a LLM.

        Args:
            llm: A LLM instance to handle query rephrasing.
        """

        self._llm = llm
        self._prompt_strategy = prompt_strategy or QueryRephraserPrompt

    async def rephrase(self, query: str, options: Optional[LLMOptions] = None) -> list[str]:
        """
        Rephrase a given query using the LLM.

        Args:
            query: The query to be rephrased. If not provided, a custom prompt must be given.
            options: Optional settings for the LLM to control generation behavior.

        Returns:
            A list containing the rephrased query.

        Raises:
            ValueError: If both `query` and `prompt` are None.
        """

        prompt_inputs = self._prompt_strategy.input_type(query=query)  # type: ignore
        prompt = self._prompt_strategy(prompt_inputs)

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
        prompt_strategy = config.get("prompt_strategy")

        if prompt_strategy is not None:
            prompt_strategy_cls = get_cls_from_config(prompt_strategy, rephrasers)

            return cls(llm=llm, prompt_strategy=prompt_strategy_cls)

        return cls(llm=llm)
