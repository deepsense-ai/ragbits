class MetadataNotFoundError(Exception):
    """
    Raised when metadata is not found in the metadata store
    """

    def __init__(self, id: str) -> None:
        super().__init__(f"Metadata not found for {id} id.")
        self.id = id
