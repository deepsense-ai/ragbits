from typing import Any

from fastapi import FastAPI

from .tool import Tool
from .tools import TOOL_HANDLERS


class IntegrationServerBuilder:
    """
    Serves as a builder for the integration server for popular LLM interfaces such as ChatGPT.

    Builder allows to integrate multiple tools into the server.
    Tools are pieces of logic that can be exposed as an API endpoint.
    Example tools are:
        - Ragbits Document search
    """
    _tools: list[Tool]

    def __init__(self):
        self._tools = []

    def add_tool(self, tool: Any, name: str | None = None, description: str | None = None):
        self._tools.append(Tool(backend=tool, name=name, description=description))
        return self

    def build(self, app: FastAPI | None = None) -> FastAPI:
        if app is None:
            app = FastAPI()

        for tool in self._tools:

            for handler in TOOL_HANDLERS:
                if handler.check(tool):
                    handler.register_in_chatgpt(tool, app)

        return app

