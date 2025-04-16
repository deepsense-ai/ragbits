import importlib
import json
import logging
import os
from collections.abc import AsyncGenerator
from pathlib import Path

import uvicorn
import yaml
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

    def __init__(
        self,
        chat_interface: type[ChatInterface] | str,
        config_path: str,
        cors_origins: list[str] | None = None,
        ui_build_dir: str | None = None,
    ) -> None:
        """
        Initialize the RagbitsAPI.

        Args:
            chat_interface: Either a ChatInterface class (recommended) or a string path to a class
                                in format "module.path:ClassName" (legacy support)
            config_path: Path to the api configuration file (YAML format).
            cors_origins: List of allowed CORS origins. If None, defaults to common development origins.
            ui_build_dir: Path to a custom UI build directory. If None, uses the default package UI.
        """
        self.app = FastAPI()
        self.chat_interface: ChatInterface | None = None
        self.config_path = (STARTED_FROM_DIR / config_path).resolve()
        self.dist_dir = Path(ui_build_dir) if ui_build_dir else Path(__file__).parent / "ui-build"
        self.cors_origins = cors_origins or []

        self.configure_app()
        self.setup_routes()
        self.setup_exception_handlers()

        self.initialize_chat_interface(chat_interface)

    def configure_app(self) -> None:
        """Configures middleware, CORS, and other settings."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.cors_origins,
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
            if not self.chat_interface:
                raise HTTPException(status_code=500, detail="Chat implementation is not initialized")

            response_generator = self.chat_interface.chat(
                message=request.message, history=request.history, context=request.context
            )

            return StreamingResponse(response_streamer(response_generator), media_type="text/event-stream")  # type: ignore

        @self.app.get("/api/config", response_class=JSONResponse)
        async def config() -> JSONResponse:
            if self.config_path:
                try:
                    with open(self.config_path) as file:
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

    def initialize_chat_interface(self, implementation: type[ChatInterface] | str) -> None:
        """Initialize the chat implementation from either a class directly or a module path.

        Args:
            implementation: Either a ChatInterface class or a string path in format "module:class"
        """
        if isinstance(implementation, str):
            module_stringified, object_stringified = implementation.split(":")
            logger.info(f"Loading chat implementation from path: {module_stringified}, class: {object_stringified}")

            module = importlib.import_module(module_stringified)
            implementation_class = getattr(module, object_stringified)
        else:
            implementation_class = implementation

        if not issubclass(implementation_class, ChatInterface):
            raise TypeError("Implementation must inherit from ChatInterface")

        self.chat_interface = implementation_class()
        logger.info(f"Initialized chat implementation: {implementation_class.__name__}")

    def run(self, host: str = "127.0.0.1", port: int = 8000) -> None:
        """
        Used for starting the API
        """
        uvicorn.run(self.app, host=host, port=port)
