import asyncio
import importlib
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

import uvicorn


async def word_streamer(text: str):
    words = text.split()
    for word in words:
        yield f"data: {word}\n\n"
        await asyncio.sleep(1)


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
            allow_origins=["http://localhost:8000"],
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
        def root() -> HTMLResponse:
            index_file = self.dist_dir / "index.html"
            return open(str(index_file)).read()

        @self.app.post("/api/chat", response_class=StreamingResponse)
        def chat() -> StreamingResponse:
            # message = "Hello, this is test message"
            # history = []
            # self.chat_module(message, history)

            lorem = "Lorem ipsum dolor sit amet, consectetur adipiscing elit."
            return StreamingResponse(word_streamer(lorem), media_type="text/event-stream")
        
    
    def initialize_chat_module(self, chat_path: str, chat_name: str):
        module = importlib.import_module(chat_path)
        self.chat_module = getattr(module, chat_name)
        

    def run(self, host="127.0.0.1", port=8000):
        """
        Used for starting the API
        """

        # if self.chat_module is None:
            # raise Exception("Cannot start api service without chat module, please provide method for handling chat tasks through chat-path and chat-name arguments")

        uvicorn.run(self.app, host=host, port=port)