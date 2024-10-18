import abc
from typing import Optional

from ragbits.core.llms.base import LLMOptions
from ragbits.core.prompt import Prompt


class QueryRephraser(abc.ABC):
    """
    Rephrases a query. Can provide multiple rephrased queries from one sentence / question.
    """

    @abc.abstractmethod
    async def rephrase(
        self, query: Optional[str] = None, prompt: Optional[Prompt] = None, options: Optional[LLMOptions] = None
    ) -> list[str]:
        """
        Rephrase a query.

        Args:
            query: The query to rephrase.
            options: Optional configuration of the the rephraser behavior.
            prompt: Optional prompt.

        Returns:
            The rephrased queries.
        """

    @classmethod
    def from_config(cls, config: dict) -> "QueryRephraser":
        """
        Create an instance of `QueryRephraser` from a configuration dictionary.

        Args:
            config: A dictionary containing configuration settings for the rephraser.

        Returns:
            An instance of the rephraser class initialized with the provided configuration.
        """

        return cls(**config)
