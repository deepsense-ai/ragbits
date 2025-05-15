from collections.abc import Iterable

from typing_extensions import Self

from ragbits.core.audit.traces import traceable
from ragbits.core.llms.base import LLM
from ragbits.core.prompt import Prompt
from ragbits.core.utils.config_handling import ObjectConstructionConfig
from ragbits.document_search.retrieval.rephrasers.base import QueryRephraser, QueryRephraserOptions
from ragbits.document_search.retrieval.rephrasers.prompts import (
    QueryRephraserInput,
    QueryRephraserPrompt,
    get_rephraser_prompt,
)


class LLMQueryRephraser(QueryRephraser[QueryRephraserOptions]):
    """
    A rephraser class that uses a LLM to rephrase queries.
    """

    options_cls = QueryRephraserOptions

    def __init__(self, llm: LLM, prompt: type[Prompt[QueryRephraserInput, str]] | None = None) -> None:
        """
        Initialize the LLMQueryRephraser with a LLM.

        Args:
            llm: A LLM instance to handle query rephrasing.
            prompt: The prompt to use for rephrasing queries.
        """
        self._llm = llm
        self._prompt = prompt or QueryRephraserPrompt

    @traceable
    async def rephrase(self, query: str, options: QueryRephraserOptions | None = None) -> Iterable[str]:
        """
        Rephrase a given query using the LLM.

        Args:
            query: The query to be rephrased. If not provided, a custom prompt must be given.
            options: The options for the rephraser.

        Returns:
            A list containing the rephrased query.

        Raises:
            LLMConnectionError: If there is a connection error with the LLM API.
            LLMStatusError: If the LLM API returns an error status code.
            LLMResponseError: If the LLM API response is invalid.
        """
        prompt = self._prompt(QueryRephraserInput(query=query))
        response = await self._llm.generate(prompt)
        return [response]

    @classmethod
    def from_config(cls, config: dict) -> Self:
        """
        Create an instance of `LLMQueryRephraser` from a configuration dictionary.

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
