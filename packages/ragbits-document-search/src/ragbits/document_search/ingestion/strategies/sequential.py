from ragbits.document_search.ingestion.strategies.batched import BatchedIngestStrategy


class SequentialIngestStrategy(BatchedIngestStrategy):
    """
    Ingest strategy that processes documents in sequence, one at a time.
    """

    def __init__(self, num_retries: int = 3, backoff_multiplier: int = 1, backoff_max: int = 60) -> None:
        """
        Initialize the SequentialIngestStrategy instance.

        Args:
            num_retries: The number of retries per document ingest task error.
            backoff_multiplier: The base delay multiplier for exponential backoff (in seconds).
            backoff_max: The maximum allowed delay (in seconds) between retries.
        """
        super().__init__(
            batch_size=1,
            num_retries=num_retries,
            backoff_multiplier=backoff_multiplier,
            backoff_max=backoff_max,
        )
