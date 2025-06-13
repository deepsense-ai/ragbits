class AgentError(Exception):
    """
    Base class for all exceptions raised by the Agent.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class AgentNotSupportedToolInResponseError(AgentError):
    """
    Raised when there is a tool type returned by an LLM that is not supported.
    """

    def __init__(
        self, tool_type: str, message: str = "There is a tool call in LLM response of type that is not supported: "
    ) -> None:
        super().__init__(message + tool_type)


class AgentNotAvailableToolSelectedError(AgentError):
    """
    Raised when there was a tool select that is not available.
    """

    def __init__(self, tool_name: str, message: str = "Selected tool is not available: ") -> None:
        super().__init__(message + tool_name)
