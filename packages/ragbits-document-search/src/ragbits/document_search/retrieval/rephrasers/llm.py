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


class QueryRephraserInput(BaseModel):
    """
    Input data for the query rephraser prompt.
    """

    query: str


class QueryRephraserPrompt(Prompt[QueryRephraserInput, str]):
    """
    Prompt for generating a rephrased user query.
    """

    system_prompt = """
        You are an expert in query rephrasing and clarity improvement.
        Your task is to return a single paraphrased version of a user's query,
        correcting any typos, handling abbreviations and improving clarity.
        Focus on making the query more precise and readable while keeping its original intent.
        Just return the rephrased query. No additional explanations are needed.
    """
    user_prompt = "Query:{{ query }}"


class LLMQueryRephraserOptions(QueryRephraserOptions, Generic[LLMClientOptionsT]):
    """
    Object representing the options for the LLM query rephraser.

    Attributes:
        llm_options: The options for the LLM.
    """

    llm_options: LLMClientOptionsT | None | NotGiven = NOT_GIVEN


class LLMQueryRephraser(QueryRephraser[LLMQueryRephraserOptions[LLMClientOptionsT]]):
    """
    A rephraser class that uses a LLM to rephrase queries.
    """

    options_cls: type[LLMQueryRephraserOptions] = LLMQueryRephraserOptions

    def __init__(
        self,
        llm: LLM[LLMClientOptionsT],
        prompt: type[Prompt[QueryRephraserInput, str]] | None = None,
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
        self._prompt = prompt or QueryRephraserPrompt

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
        prompt = self._prompt(QueryRephraserInput(query=query))
        response = await self._llm.generate(prompt, options=llm_options)
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
        """
        config["llm"] = LLM.subclass_from_config(ObjectConstructionConfig.model_validate(config["llm"]))
        config["prompt"] = (
            import_by_path(ObjectConstructionConfig.model_validate(config["prompt"]).type)
            if "prompt" in config
            else None
        )
        return super().from_config(config)
