class PromptError(Exception):
    """
    Base class for all exceptions raised by the Prompt.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class PromptWithAttachmentOfUnknownFormat(PromptError):
    """
    Raised when there is a file with an unknown format attached to the prompt.
    """

    def __init__(self) -> None:
        super().__init__("Could not determine MIME type for the attachment file")


class PromptWithAttachmentOfUnsupportedFormat(PromptError):
    """
    Raised when there is a file with an unsupported format attached to the prompt.
    """

    def __init__(self, mime_type: str) -> None:
        super().__init__(f"Unsupported MIME type for the attachment file: {mime_type}")


class PromptWithEmptyAttachment(PromptError):
    """
    Raised when there is an empty file attached to the prompt.
    """

    def __init__(self) -> None:
        super().__init__("Attachment must have either bytes data or URL provided")
