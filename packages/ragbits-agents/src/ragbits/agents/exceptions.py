class AgentError(Exception):
    """
    Base class for all exceptions raised by the Agent.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class AgentToolNotSupportedError(AgentError):
    """
    Raised when the selected tool type is not supported.
    """

    def __init__(self, tool_type: str) -> None:
        super().__init__(f"The tool call type in LLM response is not supported: {tool_type}")
        self.tool_type = tool_type


class AgentToolNotAvailableError(AgentError):
    """
    Raised when the selected tool is not available.
    """

    def __init__(self, tool_name: str) -> None:
        super().__init__(f"Selected tool is not available: {tool_name}")
        self.tool_name = tool_name
