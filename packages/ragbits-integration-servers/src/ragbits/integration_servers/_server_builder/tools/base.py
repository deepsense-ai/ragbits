import abc
from abc import ABC

from fastapi import FastAPI

from ragbits.integration_servers._server_builder.tool import Tool


class ToolHandler(ABC):

    @abc.abstractmethod
    def check(self, tool: Tool) -> bool:
        pass

    @abc.abstractmethod
    def register_in_chatgpt(self, tool: Tool, app: FastAPI) -> None:
        pass
