from collections.abc import Iterable
from typing import Generic

from pydantic import BaseModel
from typing_extensions import Self

from ragbits.core.audit.traces import traceable
from ragbits.core.llms.base import LLM, LLMClientOptionsT
from ragbits.core.prompt import Prompt
from ragbits.core.types import NOT_GIVEN, NotGiven
from ragbits.core.utils.config_handling import ObjectConstructionConfig, import_by_path
from ragbits.document_search.retrieval.rephrasers.base import QueryRephraser, QueryRephraserOptions


class LLMQueryRephraserPromptInput(BaseModel):
    """
    Input data for the query rephraser prompt.
    """

    query: str
    n: int | None = None


class LLMQueryRephraserPrompt(Prompt[LLMQueryRephraserPromptInput, list]):
    """
    Prompt for generating a rephrased user query.
    """

    system_prompt = """
        You are an expert in query rephrasing and clarity improvement.
        {%- if n and n > 1 %}
        Your task is to generate {{ n }} different versions of the given user query to retrieve relevant documents
        from a vector database. They can be phrased as statements, as they will be used as a search query.
        By generating multiple perspectives on the user query, your goal is to help the user overcome some of the
        limitations of the distance-based similarity search.
        Alternative queries should only contain information present in the original query. Do not include anything
        in the alternative query, you have not seen in the original version.
        It is VERY important you DO NOT ADD any comments or notes. Return ONLY alternative queries.
        Provide these alternative queries separated by newlines. DO NOT ADD any enumeration.
        {%- else %}
        Your task is to return a single paraphrased version of a user's query,
        correcting any typos, handling abbreviations and improving clarity.
        Focus on making the query more precise and readable while keeping its original intent.
        Just return the rephrased query. No additional explanations are needed.
        {%- endif %}
    """
    user_prompt = "Query: {{ query }}"

    @staticmethod
    def _response_parser(value: str) -> list[str]:
        return [stripped_line for line in value.strip().split("\n") if (stripped_line := line.strip())]

    response_parser = _response_parser


class LLMQueryRephraserOptions(QueryRephraserOptions, Generic[LLMClientOptionsT]):
    """
    Object representing the options for the LLM query rephraser.

    Attributes:
        n: The number of rephrasings to generate. Any number below 2 will generate only one rephrasing.
        llm_options: The options for the LLM.
    """

    n: int | None | NotGiven = NOT_GIVEN
    llm_options: LLMClientOptionsT | None | NotGiven = NOT_GIVEN


class LLMQueryRephraser(QueryRephraser[LLMQueryRephraserOptions[LLMClientOptionsT]]):
    """
    A rephraser class that uses a LLM to rephrase queries.
    """

    options_cls: type[LLMQueryRephraserOptions] = LLMQueryRephraserOptions

    def __init__(
        self,
        llm: LLM[LLMClientOptionsT],
        prompt: type[Prompt[LLMQueryRephraserPromptInput, list[str]]] | None = None,
        default_options: LLMQueryRephraserOptions[LLMClientOptionsT] | None = None,
    ) -> None:
        """
        Initialize the LLMQueryRephraser with a LLM.

        Args:
            llm: A LLM instance to handle query rephrasing.
            prompt: The prompt to use for rephrasing queries.
            default_options: The default options for the rephraser.
        """
        super().__init__(default_options=default_options)
        self._llm = llm
        self._prompt = prompt or LLMQueryRephraserPrompt

    @traceable
    async def rephrase(
        self,
        query: str,
        options: LLMQueryRephraserOptions[LLMClientOptionsT] | None = None,
    ) -> Iterable[str]:
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
        merged_options = (self.default_options | options) if options else self.default_options
        llm_options = merged_options.llm_options or None
        prompt = self._prompt(LLMQueryRephraserPromptInput(query=query, n=merged_options.n or None))
        return await self._llm.generate(prompt, options=llm_options)

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
        """
        config["llm"] = LLM.subclass_from_config(ObjectConstructionConfig.model_validate(config["llm"]))
        config["prompt"] = (
            import_by_path(ObjectConstructionConfig.model_validate(config["prompt"]).type)
            if "prompt" in config
            else None
        )
        return super().from_config(config)
