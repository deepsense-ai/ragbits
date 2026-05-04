from abc import ABC, abstractmethod

from ragbits.agents.tool import Tool

from ragbits.chat.interface.types import ChatContext


class ChatTool(ABC):
    """Base class for tools that can be registered on a ChatInterface.

    Subclass this to create a tool that the LLM can call during chat.
    Each call to ``build`` receives the current request context (session,
    authenticated user, …) and must return a ragbits ``Tool`` instance that
    is ready to execute.

    Example::

        class MyTool(ChatTool):
            # Shown in the Available Tools sidebar panel
            tool_id = "my_tool"
            display_name = "My Tool"
            category = "Utilities"

            def build(self, context: ChatContext) -> Tool:
                async def my_tool(query: str) -> str:
                    \"\"\"Run my tool.

                    Args:
                        query: The query to process.
                    \"\"\"
                    return f"Result for {query}"

                return Tool.from_callable(my_tool)
    """

    #: Unique identifier used in ``ToolEntry`` and as the LLM function name.
    tool_id: str
    #: Human-readable label shown in the sidebar panel (emoji supported).
    display_name: str
    #: Group label for the sidebar panel (e.g. ``"Utilities"``).
    category: str
    #: Whether the tool is available by default. Set to ``False`` to show a
    #: red dot in the panel without disabling the ``Tool`` itself.
    has_access: bool = True
    #: Google OAuth incremental scope group name (``"calendar"``, ``"drive"``,
    #: …).  When set, the sidebar shows a *Connect* button until the user
    #: grants the scope.
    google_scope: str | None = None

    @abstractmethod
    def build(self, context: ChatContext) -> Tool:
        """Return a ready-to-call ``Tool`` bound to this request context.

        Args:
            context: The current chat request context, including the
                authenticated user and session identifier.

        Returns:
            A ``ragbits.agents.tool.Tool`` instance the agent can invoke.
        """
