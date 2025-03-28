# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "gradio",
#     "ragbits-document-search",
#     "ragbits-core[chroma]",
# ]
# ///
from collections.abc import AsyncIterator
from pathlib import Path

import gradio as gr
from chromadb import PersistentClient
from pydantic import BaseModel

from ragbits.core.embeddings.litellm import LiteLLMEmbedder
from ragbits.core.llms.litellm import LiteLLM
from ragbits.core.prompt import Prompt
from ragbits.core.vector_stores.chroma import ChromaVectorStore
from ragbits.document_search import DocumentSearch
from ragbits.document_search.documents.document import DocumentMeta


class QueryWithContext(BaseModel):
    """
    Input format for the QueryWithContext.
    """

    query: str
    context: list[str]


class ChatAnswer(BaseModel):
    """
    Output format for the ChatAnswer.
    """

    answer: str


class RAGPrompt(Prompt[QueryWithContext, ChatAnswer]):
    """
    A simple prompt for RAG system.
    """

    system_prompt = """
    You are a helpful assistant. Answer the QUESTION that will be provided using CONTEXT.
    If in the given CONTEXT there is not enough information refuse to answer.
    """

    user_prompt = """
    QUESTION:
    {{ query }}

    CONTEXT:
    {% for item in context %}
        {{ item }}
    {% endfor %}
    """


class RAGSystemWithUI:
    """
    Simple RAG application
    """

    DATABASE_CREATED_MESSAGE = "Database created and saved at: "
    DATABASE_LOADED_MESSAGE = "Database loaded"
    NO_DOCUMENTS_INGESTED_MESSAGE = (
        "Before making queries you need to select documents and create database or "
        "provide a path to an existing database"
    )
    DOCUMENT_PICKER_LABEL = "Documents"
    DATABASE_TEXT_BOX_LABEL = "Database path"
    DATABASE_CREATE_BUTTON_LABEL = "Create Database"
    DATABASE_LOAD_BUTTON_LABEL = "Load Database"
    DATABASE_CREATION_STATUS_LABEL = "Database creation status"
    DATABASE_CREATION_STATUS_PLACEHOLDER = "Upload files and click 'Create Database' to start..."
    DATABASE_LOADING_STATUS_LABEL = "Database loading status"
    DATABASE_LOADING_STATUS_PLACEHOLDER = "Click 'Load Database' to start..."

    def __init__(
        self,
        database_path: str = "chroma",
        index_name: str = "documents",
        model_name: str = "gpt-4o-2024-08-06",
        columns_ratios: tuple[int, int] = (1, 5),
        chatbot_height_vh: int = 90,
    ) -> None:
        self._database_path = database_path
        self._index_name = index_name
        self._columns_ratios = columns_ratios
        self._chatbot_height_vh = chatbot_height_vh
        self._documents_ingested = False
        self._prepare_document_search(self._database_path, self._index_name)
        self._llm = LiteLLM(model_name, use_structured_output=True)

    def _prepare_document_search(self, database_path: str, index_name: str) -> None:
        embedder = LiteLLMEmbedder()
        vector_store = ChromaVectorStore(
            client=PersistentClient(database_path),
            index_name=index_name,
            embedder=embedder,
        )
        self.document_search = DocumentSearch(
            vector_store=vector_store,
        )

    async def _create_database(self, document_paths: list[str]) -> str:
        for path in document_paths:
            await self.document_search.ingest([DocumentMeta.from_local_path(Path(path))])
        self._documents_ingested = True
        return self.DATABASE_CREATED_MESSAGE + self._database_path

    def _load_database(self, database_path: str) -> str:
        self._prepare_document_search(database_path, self._index_name)
        self._documents_ingested = True
        return self.DATABASE_LOADED_MESSAGE

    async def _handle_message(
        self,
        message: str,
        history: list[dict],  # pylint: disable=unused-argument
    ) -> AsyncIterator[str]:
        if not self._documents_ingested:
            yield self.NO_DOCUMENTS_INGESTED_MESSAGE
        results = await self.document_search.search(message[-1])
        prompt = RAGPrompt(
            QueryWithContext(query=message, context=[i.text_representation for i in results if i.text_representation])
        )
        response = await self._llm.generate(prompt)
        yield response.answer

    def prepare_layout(self) -> gr.Blocks:
        """
        Crates gradio layout as gr.Blocks and connects component events with proper handlers

        Returns:
            gradio layout
        """
        with gr.Blocks(fill_height=True, fill_width=True) as app, gr.Row():
            with gr.Column(scale=self._columns_ratios[0]):
                with gr.Group():
                    documents_picker = gr.File(file_count="multiple", label=self.DOCUMENT_PICKER_LABEL)
                    create_btn = gr.Button(self.DATABASE_CREATE_BUTTON_LABEL)
                    creating_status_display = gr.Textbox(
                        label=self.DATABASE_CREATION_STATUS_LABEL,
                        interactive=False,
                        placeholder=self.DATABASE_CREATION_STATUS_PLACEHOLDER,
                    )

                with gr.Group():
                    database_path = gr.Textbox(label=self.DATABASE_TEXT_BOX_LABEL)
                    load_btn = gr.Button(self.DATABASE_LOAD_BUTTON_LABEL)
                    loading_status_display = gr.Textbox(
                        label=self.DATABASE_LOADING_STATUS_LABEL,
                        interactive=False,
                        placeholder=self.DATABASE_LOADING_STATUS_PLACEHOLDER,
                    )
                load_btn.click(fn=self._load_database, inputs=database_path, outputs=loading_status_display)
                create_btn.click(fn=self._create_database, inputs=documents_picker, outputs=creating_status_display)

            with gr.Column(scale=self._columns_ratios[1]):
                chat_interface = gr.ChatInterface(self._handle_message, type="messages")
                chat_interface.chatbot.height = f"{self._chatbot_height_vh}vh"
        return app


if __name__ == "__main__":
    rag_system = RAGSystemWithUI()
    rag_system.prepare_layout().launch()
