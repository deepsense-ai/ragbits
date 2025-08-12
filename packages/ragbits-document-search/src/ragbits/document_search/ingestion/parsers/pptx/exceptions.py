from ragbits.document_search.ingestion.parsers.exceptions import ParserError


class PptxParserError(ParserError):
    """
    Base class for all PPTX parser related exceptions.
    """


class PptxExtractionError(PptxParserError):
    """
    Raised when an extractor fails to extract content from a shape or slide.
    """

    def __init__(self, extractor_name: str, slide_idx: int, shape_info: str, original_error: Exception) -> None:
        """
        Initialize the PptxExtractionError.

        Args:
            extractor_name: Name of the extractor that failed.
            slide_idx: Index of the slide where extraction failed.
            shape_info: Information about the shape that caused the failure.
            original_error: The original exception that caused the failure.
        """
        message = (
            f"Extractor '{extractor_name}' failed to extract content from slide {slide_idx}. "
            f"Shape info: {shape_info}. Original error: {original_error}"
        )
        super().__init__(message)
        self.extractor_name = extractor_name
        self.slide_idx = slide_idx
        self.shape_info = shape_info
        self.original_error = original_error


class PptxPresentationError(PptxParserError):
    """
    Raised when the PPTX presentation cannot be loaded or processed.
    """

    def __init__(self, file_path: str, original_error: Exception) -> None:
        """
        Initialize the PptxPresentationError.

        Args:
            file_path: Path to the PPTX file that failed to load.
            original_error: The original exception that caused the failure.
        """
        message = f"Failed to load or process PPTX presentation from '{file_path}'. Original error: {original_error}"
        super().__init__(message)
        self.file_path = file_path
        self.original_error = original_error
