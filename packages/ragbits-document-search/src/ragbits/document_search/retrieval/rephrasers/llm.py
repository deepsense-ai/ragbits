from typing import Any

from ragbits.core.audit import traceable
from ragbits.core.llms.base import LLM
from ragbits.core.prompt import Prompt
from ragbits.core.utils.config_handling import ObjectContructionConfig
from ragbits.document_search.retrieval.rephrasers.base import QueryRephraser
from ragbits.document_search.retrieval.rephrasers.prompts import (
    QueryRephraserInput,
    QueryRephraserPrompt,
    get_rephraser_prompt,
)


class LLMQueryRephraser(QueryRephraser):
    """
    A rephraser class that uses a LLM to rephrase queries.
    """

    def __init__(self, llm: LLM, prompt: type[Prompt[QueryRephraserInput, Any]] | None = None):
        """
        Initialize the LLMQueryRephraser with a LLM.

        Args:
            llm: A LLM instance to handle query rephrasing.
            prompt: The prompt to use for rephrasing queries.
        """
        self._llm = llm
        self._prompt = prompt or QueryRephraserPrompt

    @traceable
    async def rephrase(self, query: str) -> list[str]:
        """
        Rephrase a given query using the LLM.

        Args:
            query: The query to be rephrased. If not provided, a custom prompt must be given.

        Returns:
            A list containing the rephrased query.

        Raises:
            LLMConnectionError: If there is a connection error with the LLM API.
            LLMStatusError: If the LLM API returns an error status code.
            LLMResponseError: If the LLM API response is invalid.
        """
        input_data = self._prompt.input_type(query=query)  # type: ignore
        prompt = self._prompt(input_data)
        response = await self._llm.generate(prompt)
        return response if isinstance(response, list) else [response]

    @classmethod
    def from_config(cls, config: dict) -> "LLMQueryRephraser":
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
        llm: LLM = LLM.subclass_from_config(ObjectContructionConfig.model_validate(config["llm"]))
        prompt_cls = None
        if "prompt" in config:
            prompt_config = ObjectContructionConfig.model_validate(config["prompt"])
            prompt_cls = get_rephraser_prompt(prompt_config.type)
        return cls(llm=llm, prompt=prompt_cls)
