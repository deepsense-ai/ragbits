from collections.abc import Sequence

from fastapi import FastAPI

from ragbits.integration_servers._server_builder.tool import Tool
from ragbits.integration_servers._server_builder.tools.base import ToolHandler


class DocumentSearchToolHandler(ToolHandler):

    def check(self, tool: Tool) -> bool:
        try:
            from ragbits.document_search import DocumentSearch
        except ImportError:
            return False

        return isinstance(tool.backend, DocumentSearch)

    def register_in_chatgpt(self, tool: Tool, app: FastAPI) -> None:
        from ragbits.document_search.documents.element import Element

        @app.get(f"/{tool.name}" if tool.name else "/document-search")
        async def document_search(query: str) -> Sequence[Element]:
            result = await tool.backend.search(query)
            return result

        document_search.__doc__ = tool.description or document_search.__doc__
