from ragbits.document_search.retrieval.rephrasers.base import QueryRephraser


class NoopQueryRephraser(QueryRephraser):
    """A no-op query paraphraser that does not change the query.
    """

    @staticmethod
    def rephrase(query: str) -> list[str]:
        """Mock implementation which outputs the same query as in input.

        Args:
            query: The query to rephrase.

        Returns:
            The list with non-transformed query.
        """
        return [query]
