import importlib
import json
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import ChatContext, ChatResponse, Message

logger = logging.getLogger(__name__)


class ChatMessageRequest(BaseModel):
    """
    Request body for chat message
    """

    message: str = Field(..., description="The current user message")
    history: list[Message] = Field(default_factory=list, description="Previous message history")
    context: dict[str, Any] = Field(default_factory=dict, description="User context information")


class FeedbackRequest(BaseModel):
    """
    Request body for feedback submission
    """

    message_id: str = Field(..., description="ID of the message receiving feedback")
    feedback: Literal["like", "dislike"] = Field(..., description="Type of feedback (like or dislike)")
    payload: dict = Field(default_factory=dict, description="Additional feedback details")


class RagbitsAPI:
    """
    RagbitsAPI class for running API with Demo UI for testing purposes
    """

    def __init__(
        self,
        chat_interface: type[ChatInterface] | str,
        cors_origins: list[str] | None = None,
        ui_build_dir: str | None = None,
    ) -> None:
        """
        Initialize the RagbitsAPI.

        Args:
            chat_interface: Either a ChatInterface class (recommended) or a string path to a class
                                in format "module.path:ClassName" (legacy support)
            cors_origins: List of allowed CORS origins. If None, defaults to common development origins.
            ui_build_dir: Path to a custom UI build directory. If None, uses the default package UI.
        """
        self.chat_interface: ChatInterface = self._load_chat_interface(chat_interface)
        self.dist_dir = Path(ui_build_dir) if ui_build_dir else Path(__file__).parent / "ui-build"
        self.cors_origins = cors_origins or []

        @asynccontextmanager
        async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
            await self.chat_interface.setup()
            yield

        self.app = FastAPI(lifespan=lifespan)

        self.configure_app()
        self.setup_routes()
        self.setup_exception_handlers()

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

            # Convert request context to ChatContext
            chat_context = ChatContext(**request.context)

            # Verify state signature if provided
            if "state" in request.context and "signature" in request.context:
                state = request.context["state"]
                signature = request.context["signature"]
                if not ChatInterface.verify_state(state, signature):
                    logger.warning(f"Invalid state signature received for message {chat_context.message_id}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid state signature",
                    )
                # Remove the signature from context after verification (it's already parsed into ChatContext)

            # Get the response generator from the chat interface
            response_generator = self.chat_interface.chat(
                message=request.message,
                history=[msg.model_dump() for msg in request.history],
                context=chat_context,
            )

            # Pass the generator to the SSE formatter
            return StreamingResponse(
                RagbitsAPI._chat_response_to_sse(response_generator),
                media_type="text/event-stream",
            )

        @self.app.post("/api/feedback", response_class=JSONResponse)
        async def feedback(request: FeedbackRequest) -> JSONResponse:
            """Handle user feedback for chat messages."""
            if not self.chat_interface:
                raise HTTPException(status_code=500, detail="Chat implementation is not initialized")

            await self.chat_interface.save_feedback(
                message_id=request.message_id,
                feedback=request.feedback,
                payload=request.payload,
            )

            return JSONResponse(content={"status": "success"})

        @self.app.get("/api/config", response_class=JSONResponse)
        async def config() -> JSONResponse:
            config_dict = {
                "feedback": {
                    "like": {
                        "enabled": self.chat_interface.feedback_config.like_enabled,
                        "form": self.chat_interface.feedback_config.like_form.model_dump()
                        if self.chat_interface.feedback_config.like_form
                        else None,
                    },
                    "dislike": {
                        "enabled": self.chat_interface.feedback_config.dislike_enabled,
                        "form": self.chat_interface.feedback_config.dislike_form.model_dump()
                        if self.chat_interface.feedback_config.dislike_form
                        else None,
                    },
                }
            }

            return JSONResponse(content=config_dict)

    @staticmethod
    async def _chat_response_to_sse(
        responses: AsyncGenerator[ChatResponse],
    ) -> AsyncGenerator[str, None]:
        """
        Formats chat responses into Server-Sent Events (SSE) format for streaming to the client.
        Each response is converted to JSON and wrapped in the SSE 'data:' prefix.

        Args:
            responses: The chat response generator
        """
        async for response in responses:
            data = json.dumps(
                {
                    "type": response.type.value,
                    "content": response.content if isinstance(response.content, str) else response.content.model_dump(),
                }
            )
            yield f"data: {data}\n\n"

    @staticmethod
    def _load_chat_interface(implementation: type[ChatInterface] | str) -> ChatInterface:
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

        logger.info(f"Initialized chat implementation: {implementation_class.__name__}")
        return implementation_class()

    def run(self, host: str = "127.0.0.1", port: int = 8000) -> None:
        """
        Used for starting the API
        """
        uvicorn.run(self.app, host=host, port=port)
