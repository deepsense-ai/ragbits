from collections.abc import Iterable
from typing import Any

from typing_extensions import Self

from ragbits.core.audit.traces import traceable
from ragbits.core.llms.base import LLM
from ragbits.core.prompt import Prompt
from ragbits.core.utils.config_handling import ObjectConstructionConfig
from ragbits.document_search.retrieval.rephrasers.base import QueryRephraser, QueryRephraserOptions
from ragbits.document_search.retrieval.rephrasers.prompts import (
    MultiQueryRephraserInput,
    MultiQueryRephraserPrompt,
    get_rephraser_prompt,
)


class MultiQueryRephraserOptions(QueryRephraserOptions):
    """
    Object representing the options for the multi query rephraser.

    Attributes:
        n: The number of rephrasings to generate.
    """

    n: int = 5


class MultiQueryRephraser(QueryRephraser[MultiQueryRephraserOptions]):
    """
    A rephraser class that uses a LLM to generate reworded versions of input query.
    """

    options_cls = MultiQueryRephraserOptions

    def __init__(
        self,
        llm: LLM,
        prompt: type[Prompt[MultiQueryRephraserInput, Any]] | None = None,
        default_options: MultiQueryRephraserOptions | None = None,
    ):
        """
        Initialize the MultiQueryRephraser with a LLM.

        Args:
            llm: A LLM instance to handle query rephrasing.
            prompt: The prompt to use for rephrasing queries.
            default_options: The default options for the rephraser.
        """
        super().__init__(default_options=default_options)
        self._llm = llm
        self._prompt = prompt or MultiQueryRephraserPrompt

    @traceable
    async def rephrase(self, query: str, options: QueryRephraserOptions | None = None) -> Iterable[str]:
        """
        Rephrase a given query using the LLM.

        Args:
            query: The query to be rephrased. If not provided, a custom prompt must be given.
            options: The options for the rephraser.

        Returns:
            A list containing the reworded versions of input query.

        Raises:
            LLMConnectionError: If there is a connection error with the LLM API.
            LLMStatusError: If the LLM API returns an error status code.
            LLMResponseError: If the LLM API response is invalid.
        """
        merged_options = (self.default_options | options) if options else self.default_options
        input_data = self._prompt.input_type(query=query, n=merged_options.n)  # type: ignore
        prompt = self._prompt(input_data)
        response = await self._llm.generate(prompt)
        return [query] + response

    @classmethod
    def from_config(cls, config: dict) -> Self:
        """
        Create an instance of `MultiQueryRephraser` from a configuration dictionary.

        Args:
            config: A dictionary containing configuration settings for the rephraser.

        Returns:
            An instance of the rephraser class initialized with the provided configuration.

        Raises:
           ValidationError: If the LLM or prompt configuration doesn't follow the expected format.
           InvalidConfigError: If an LLM or prompt class can't be found or is not the correct type.
           ValueError: If the prompt class is not a subclass of `Prompt`.
        """
        config["llm"] = LLM.subclass_from_config(ObjectConstructionConfig.model_validate(config["llm"]))
        config["prompt"] = (
            get_rephraser_prompt(ObjectConstructionConfig.model_validate(config["prompt"]).type)
            if "prompt" in config
            else None
        )
        return super().from_config(config)
