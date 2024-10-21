from typing import Optional

from ragbits.core.llms.base import LLMOptions
from ragbits.document_search.retrieval.rephrasers.base import QueryRephraser


class NoopQueryRephraser(QueryRephraser):
    """
    A no-op query paraphraser that does not change the query.
    """

    async def rephrase(
        self,
        query: str,
        options: Optional[LLMOptions] = None,  # pylint: disable=unused-argument
    ) -> list[str]:
        """
        Mock implementation which outputs the same query as in input.

        Args:
            query: The query to rephrase.
            options: Optional configuration of the the rephraser behavior.

        Returns:
            The list with non-transformed query.

        Raises:
            ValueError: If both `query` and `prompt` are None.
        """

        if not isinstance(query, str):
            raise ValueError("`query` must be provided.")

        return [query]
