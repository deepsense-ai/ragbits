from typing import Optional

from ragbits.core.llms.base import LLMOptions
from ragbits.core.prompt import Prompt
from ragbits.document_search.retrieval.rephrasers.base import QueryRephraser


class NoopQueryRephraser(QueryRephraser):
    """
    A no-op query paraphraser that does not change the query.
    """

    async def rephrase(
        self,
        query: Optional[str] = None,
        prompt: Optional[Prompt] = None,  # pylint: disable=unused-argument
        options: Optional[LLMOptions] = None,  # pylint: disable=unused-argument
    ) -> list[str]:
        """
        Mock implementation which outputs the same query as in input.

        Args:
            query: The query to rephrase.
            options: Optional configuration of the the rephraser behavior.
            prompt: Optional prompt.

        Returns:
            The list with non-transformed query.

        Raises:
            ValueError: If both `query` and `prompt` are None.
        """

        if not isinstance(query, str):
            raise ValueError("`query` must be provided.")

        return [query]
