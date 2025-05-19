from collections.abc import Iterable

from pydantic import BaseModel
from typing_extensions import Self

from ragbits.core.audit.traces import traceable
from ragbits.core.llms.base import LLM, LLMClientOptionsT
from ragbits.core.prompt import Prompt
from ragbits.core.utils.config_handling import ObjectConstructionConfig, import_by_path
from ragbits.document_search.retrieval.rephrasers.base import QueryRephraser
from ragbits.document_search.retrieval.rephrasers.llm import LLMQueryRephraserOptions


class MultiQueryRephraserInput(BaseModel):
    """
    Input data for the multi query rephraser prompt.
    """

    query: str
    n: int


class MultiQueryRephraserPrompt(Prompt[MultiQueryRephraserInput, list]):
    """
    Prompt for generating multiple query rephrasings.
    """

    system_prompt = """
        You are a helpful assistant that creates short rephrased versions of a given query.
        Your task is to generate {{ n }} different versions of the given user query to retrieve relevant documents
        from a vector database. They can be phrased as statements, as they will be used as a search query.
        By generating multiple perspectives on the user query, your goal is to help the user overcome some of the
        limitations of the distance-based similarity search.
        Alternative queries should only contain information present in the original query. Do not include anything
        in the alternative query, you have not seen in the original version.
        It is VERY important you DO NOT ADD any comments or notes. Return ONLY alternative queries.
        Provide these alternative queries separated by newlines.
        DO NOT ADD any enumeration.
    """
    user_prompt = "Query: {{ query }}"

    @staticmethod
    def _list_parser(value: str) -> list[str]:
        return value.split("\n")

    response_parser = _list_parser


class MultiQueryRephraserOptions(LLMQueryRephraserOptions[LLMClientOptionsT]):
    """
    Object representing the options for the multi query rephraser.

    Attributes:
        llm_options: The options for the LLM.
        n: The number of rephrasings to generate.
    """

    n: int = 5


class MultiQueryRephraser(QueryRephraser[MultiQueryRephraserOptions[LLMClientOptionsT]]):
    """
    A rephraser class that uses a LLM to generate reworded versions of input query.
    """

    options_cls: type[MultiQueryRephraserOptions] = MultiQueryRephraserOptions

    def __init__(
        self,
        llm: LLM[LLMClientOptionsT],
        prompt: type[Prompt[MultiQueryRephraserInput, list[str]]] | None = None,
        default_options: MultiQueryRephraserOptions[LLMClientOptionsT] | None = None,
    ) -> None:
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
    async def rephrase(
        self,
        query: str,
        options: MultiQueryRephraserOptions[LLMClientOptionsT] | None = None,
    ) -> Iterable[str]:
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
        llm_options = merged_options.llm_options or None
        prompt = self._prompt(MultiQueryRephraserInput(query=query, n=merged_options.n))
        response = await self._llm.generate(prompt, options=llm_options)
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
        """
        config["llm"] = LLM.subclass_from_config(ObjectConstructionConfig.model_validate(config["llm"]))
        config["prompt"] = (
            import_by_path(ObjectConstructionConfig.model_validate(config["prompt"]).type)
            if "prompt" in config
            else None
        )
        return super().from_config(config)
