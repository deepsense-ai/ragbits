import importlib
import os
import json
import yaml
import logging
from collections.abc import AsyncGenerator
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ragbits.api.interface import ChatInterface
from ragbits.api.interface.types import ChatResponse, Message

logger = logging.getLogger(__name__)

STARTED_FROM_DIR = Path(os.getcwd()).resolve()


class ChatMessageRequest(BaseModel):
    message: str = Field(..., description="The current user message")
    history: list[Message] = Field(default_factory=list, description="Previous message history")
    context: dict[str, str | None] = Field(default_factory=dict, description="User context information")


async def response_streamer(responses: AsyncGenerator[ChatResponse]) -> AsyncGenerator[str, None]:
    async for response in responses:
        data = json.dumps(
            {
                "type": response.type.value,
                "content": response.content if isinstance(response.content, str) else response.content.model_dump(),
            }
        )
        yield f"data: {data}\n\n"


class RagbitsAPI:
    """
    RagbitsAPI class for running API with Demo UI for testing purposes
    """

    def __init__(self, chat_implementation: type[ChatInterface] | str, config_path: str) -> None:
        """
        Initialize the RagbitsAPI.

        Args:
            chat_implementation: Either a ChatInterface class (recommended) or a string path to a class
                                in format "module.path:ClassName" (legacy support)
        """
        self.app = FastAPI()
        self.chat_implementation: ChatInterface | None = None
        self.config_path = (STARTED_FROM_DIR / config_path).resolve()
        self.dist_dir = Path(__file__).parent / "ui-build"
        self.configure_app()
        self.setup_routes()
        self.setup_exception_handlers()

        self.initialize_chat_implementation(chat_implementation)

    def configure_app(self) -> None:
        """Configures middleware, CORS, and other settings."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=[
                "http://localhost:8000",
                "http://localhost:5173",
                "http://localhost:8081",
                "http://127.0.0.1:8000",
                "http://127.0.0.1:5173",
                "http://127.0.0.1:8081",
            ],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        assets_dir = self.dist_dir / "assets"
        static_dir = self.dist_dir / "static"
        # Note: Assets directory is always produced by the build process, but static directory is optional
        self.app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
        if static_dir.exists():
            self.app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    def setup_exception_handlers(self) -> None:
        """Setup custom exception handlers."""

        @self.app.exception_handler(RequestValidationError)
        async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
            """Handle validation errors in a structured way."""
            logger.error(f"Validation error: {exc}")
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": exc.errors(), "body": exc.body},
            )

    def setup_routes(self) -> None:
        """Defines API routes."""

        @self.app.get("/", response_class=HTMLResponse)
        async def root() -> HTMLResponse:
            index_file = self.dist_dir / "index.html"
            with open(str(index_file)) as file:
                return HTMLResponse(content=file.read())

        @self.app.post("/api/chat", response_class=StreamingResponse)
        async def chat_message(request: ChatMessageRequest) -> StreamingResponse:
            if not self.chat_implementation:
                raise HTTPException(status_code=500, detail="Chat implementation is not initialized")

            response_generator = self.chat_implementation.chat(
                message=request.message, history=request.history, context=request.context
            )

            return StreamingResponse(response_streamer(response_generator), media_type="text/event-stream")  # type: ignore

        @self.app.get("/api/config", response_class=JSONResponse)
        async def config() -> JSONResponse:
            if self.config_path:
                try:
                    with open(self.config_path, "r") as file:
                        config_data = yaml.safe_load(file)
                    return JSONResponse(content=config_data)
                except Exception as e:
                    logger.error(f"Error reading config file: {e}")
                    return JSONResponse(
                        status_code=500,
                        content={"detail": f"Error reading config file: {e}"},
                    )
            else:
                return JSONResponse(content={})

    def initialize_chat_implementation(self, implementation: type[ChatInterface] | str) -> None:
        """Initialize the chat implementation from either a class directly or a module path.

        Args:
            implementation: Either a ChatInterface class or a string path in format "module:class"
        """
        if isinstance(implementation, str):
            # Handle string path case (legacy support)
            module_stringified, object_stringified = implementation.split(":")
            logger.info(f"Loading chat implementation from path: {module_stringified}, class: {object_stringified}")

            module = importlib.import_module(module_stringified)
            implementation_class = getattr(module, object_stringified)
        else:
            implementation_class = implementation

        if not issubclass(implementation_class, ChatInterface):
            raise TypeError("Implementation must inherit from ChatInterface")

        self.chat_implementation = implementation_class()
        logger.info(f"Initialized chat implementation: {implementation_class.__name__}")

    def run(self, host: str = "127.0.0.1", port: int = 8000) -> None:
        """
        Used for starting the API
        """
        uvicorn.run(self.app, host=host, port=port)
