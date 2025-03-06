class PromptError(Exception):
    """
    Base class for all exceptions raised by the Prompt.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class PromptWithImagesOfInvalidFormat(PromptError):
    """
    Raised when there is an image attached to the prompt that is not in the correct format.
    """

    def __init__(
        self, message: str = "Invalid format of image in prompt detected. Use one of supported OpenAI mime types"
    ) -> None:
        super().__init__(message)
