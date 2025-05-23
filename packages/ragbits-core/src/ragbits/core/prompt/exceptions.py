class PromptError(Exception):
    """
    Base class for all exceptions raised by the Prompt.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class PromptWithAttachmentsOfInvalidFormat(PromptError):
    """
    Raised when there is an image or file attached to the prompt that is not in the correct format.
    """

    def __init__(
        self, message: str = "Invalid format of image or file in prompt detected. Use one of supported OpenAI mime types"
    ) -> None:
        super().__init__(message)
