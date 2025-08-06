class LLMError(Exception):
    """
    Base class for all exceptions raised by the LLMClient.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class LLMConnectionError(LLMError):
    """
    Raised when there is an error connecting to the LLM API.
    """

    def __init__(self, message: str = "Connection error.") -> None:
        super().__init__(message)


class LLMStatusError(LLMError):
    """
    Raised when an API response has a status code of 4xx or 5xx.
    """

    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class LLMResponseError(LLMError):
    """
    Raised when an API response has an invalid schema.
    """

    def __init__(self, message: str = "Data returned by API invalid for expected schema.") -> None:
        super().__init__(message)


class LLMEmptyResponseError(LLMError):
    """
    Raised when an API response is empty.
    """

    def __init__(self, message: str = "Empty response returned by API.") -> None:
        super().__init__(message)


class LLMNotSupportingImagesError(LLMError):
    """
    Raised when there are images in the prompt, but LLM doesn't support them.
    """

    def __init__(self, message: str = "There are images in the prompt, but given LLM doesn't support them.") -> None:
        super().__init__(message)


class LLMNotSupportingPdfsError(LLMError):
    """
    Raised when there are PDFs in the prompt, but LLM doesn't support them.
    """

    def __init__(self, message: str = "There are PDFs in the prompt, but given LLM doesn't support them.") -> None:
        super().__init__(message)


class LLMNotSupportingToolUseError(LLMError):
    """
    Raised when there are tools provided, but LLM doesn't support tool use.
    """

    def __init__(self, message: str = "There are tools provided, but given LLM doesn't support tool use.") -> None:
        super().__init__(message)


class LLMNotSupportingReasoningEffortError(LLMError):
    """
    Raised when there is reasoning effort provided, but LLM doesn't support it.
    """

    def __init__(self, model_name: str) -> None:
        super().__init__(f"Model {model_name} does not support reasoning effort.")
