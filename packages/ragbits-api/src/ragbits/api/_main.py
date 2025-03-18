import asyncio
import importlib
from pathlib import Path
import random
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

import uvicorn

# In-memory store for chat messages for developing purposes
chats = {}
counter = 1


async def word_streamer(text: str):
    words = text.split()
    i = 0
    while i < len(words):
        batch_size = random.randint(10, 25)
        chunk = words[i : i + batch_size]
        yield f"data: {' '.join(chunk)}\n\n"
        i += batch_size
        await asyncio.sleep(0.15)


class RagbitsAPI:
    """
    RagbitsAPI class for running API with Demo UI for testing purposes
    """

    def __init__(self):
        self.app = FastAPI()
        self.chat_module = None
        self.dist_dir = Path(__file__).parent / "ui-build"
        self.configure_app()
        self.setup_routes()

    def configure_app(self):
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

    def setup_routes(self):
        """Defines API routes."""

        @self.app.get("/", response_class=HTMLResponse)
        async def root() -> HTMLResponse:
            index_file = self.dist_dir / "index.html"
            return open(str(index_file)).read()

        @self.app.get("/api/chat/{id}", response_class=StreamingResponse)
        async def chat(id: int) -> StreamingResponse:
            question = chats.get(id)
            if not question:
                raise HTTPException(status_code=404, detail="Chat not found")

            response = await self.chat_module(question=question)
            return StreamingResponse(word_streamer(response), media_type="text/event-stream")

        @self.app.post("/api/chat", response_class=JSONResponse)
        async def chat(request: Request) -> JSONResponse:
            global counter

            data = await request.json()
            message = data.get("message")

            if not message:
                raise HTTPException(status_code=400, detail="Message is required")

            print(counter)
            chat_id = counter
            chats[chat_id] = message
            counter += 1

            return JSONResponse(content={"id": chat_id})

    def initialize_chat_module(self, chat_path: str):
        module_stringified, object_stringified = chat_path.split(":")
        print(module_stringified, object_stringified)
        module = importlib.import_module(module_stringified)
        self.chat_module = getattr(module, object_stringified)

    def run(self, host="127.0.0.1", port=8000):
        """
        Used for starting the API
        """

        # if self.chat_module is None:
        # raise Exception("Cannot start api service without chat module, please provide method for handling chat tasks through chat-path and chat-name arguments")

        uvicorn.run(self.app, host=host, port=port)
