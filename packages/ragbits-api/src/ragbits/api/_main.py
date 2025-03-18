import asyncio
import importlib
import random
from collections.abc import AsyncGenerator
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles


# Singleton class with in-memory store for chat messages, only for developing purposes
class ChatStore:
    _instance = None

    chats: dict[int, str]
    counter: int

    def __new__(cls) -> "ChatStore":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.chats = {}
            cls._instance.counter = 1
        return cls._instance


async def word_streamer(text: str) -> AsyncGenerator[str, None]:
    words = text.split()
    i = 0
    while i < len(words):
        batch_size = random.randint(10, 25)  # noqa: S311
        chunk = words[i : i + batch_size]
        yield f"data: {' '.join(chunk)}\n\n"
        i += batch_size
        await asyncio.sleep(0.15)


class RagbitsAPI:
    """
    RagbitsAPI class for running API with Demo UI for testing purposes
    """

    def __init__(self) -> None:
        self.app = FastAPI()
        self.chat_module = None
        self.dist_dir = Path(__file__).parent / "ui-build"
        self.configure_app()
        self.setup_routes()

    def configure_app(self) -> None:
        """Configures middleware, CORS, and other settings."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:8000", "http://localhost:5173"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        assets_dir = self.dist_dir / "assets"
        static_dir = self.dist_dir / "static"
        self.app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="static")
        self.app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    def setup_routes(self) -> None:
        """Defines API routes."""

        @self.app.get("/", response_class=HTMLResponse)
        async def root() -> HTMLResponse:
            index_file = self.dist_dir / "index.html"
            with open(str(index_file)) as file:
                return HTMLResponse(content=file.read())

        @self.app.get("/api/chat/{id}", response_class=StreamingResponse)
        async def chat_init(id: int) -> StreamingResponse:
            chats = ChatStore().chats
            question = chats.get(id)
            if not question:
                raise HTTPException(status_code=404, detail="Chat not found")

            if not self.chat_module:
                raise HTTPException(status_code=500, detail="Chat module is not initialized")

            response = await self.chat_module(question=question)
            return StreamingResponse(word_streamer(response), media_type="text/event-stream")

        @self.app.post("/api/chat", response_class=JSONResponse)
        async def chat_message(request: Request) -> JSONResponse:
            data = await request.json()
            message = data.get("message")

            if not message:
                raise HTTPException(status_code=400, detail="Message is required")

            counter = ChatStore().counter
            chats = ChatStore().chats
            chat_id = counter
            chats[chat_id] = message
            ChatStore().counter += 1

            return JSONResponse(content={"id": chat_id})

    def initialize_chat_module(self, chat_path: str) -> None:
        module_stringified, object_stringified = chat_path.split(":")
        print(f"Parsed chat module path: {module_stringified}, method: {object_stringified}")
        module = importlib.import_module(module_stringified)
        self.chat_module = getattr(module, object_stringified)

    def run(self, host: str = "127.0.0.1", port: int = 8000) -> None:
        """
        Used for starting the API
        """
        uvicorn.run(self.app, host=host, port=port)
