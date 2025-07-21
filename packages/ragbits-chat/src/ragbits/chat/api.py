import importlib
import json
import logging
import time
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
from ragbits.chat.interface.types import ChatContext, ChatResponse, ChatResponseType, Message
from ragbits.core.audit.metrics import record_metric
from ragbits.core.audit.metrics.base import MetricType
from ragbits.core.audit.traces import trace

from .metrics import ChatCounterMetric, ChatHistogramMetric

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
        debug_mode: bool = False,
    ) -> None:
        """
        Initialize the RagbitsAPI.

        Args:
            chat_interface: Either a ChatInterface class (recommended) or a string path to a class
                                in format "module.path:ClassName" (legacy support)
            cors_origins: List of allowed CORS origins. If None, defaults to common development origins.
            ui_build_dir: Path to a custom UI build directory. If None, uses the default package UI.
            debug_mode: Flag enabling debug tools in the default UI
        """
        self.chat_interface: ChatInterface = self._load_chat_interface(chat_interface)
        self.dist_dir = Path(ui_build_dir) if ui_build_dir else Path(__file__).parent / "ui-build"
        self.cors_origins = cors_origins or []
        self.debug_mode = debug_mode

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
            return await self._handle_chat_message(request)

        @self.app.post("/api/feedback", response_class=JSONResponse)
        async def feedback(request: FeedbackRequest) -> JSONResponse:
            return await self._handle_feedback(request)

        @self.app.get("/api/config", response_class=JSONResponse)
        async def config() -> JSONResponse:
            like_config = self.chat_interface.feedback_config.like_form
            dislike_config = self.chat_interface.feedback_config.dislike_form
            user_settings_config = self.chat_interface.user_settings.form

            config_dict = {
                "feedback": {
                    "like": {
                        "enabled": self.chat_interface.feedback_config.like_enabled,
                        "form": like_config,
                    },
                    "dislike": {
                        "enabled": self.chat_interface.feedback_config.dislike_enabled,
                        "form": dislike_config,
                    },
                },
                "customization": self.chat_interface.ui_customization.model_dump()
                if self.chat_interface.ui_customization
                else None,
                "user_settings": {"form": user_settings_config},
                "debug_mode": self.debug_mode,
            }

            return JSONResponse(content=config_dict)

    async def _handle_chat_message(self, request: ChatMessageRequest) -> StreamingResponse:  # noqa: PLR0915
        """Handle chat message requests with metrics tracking."""
        start_time = time.time()

        # Track API request
        record_metric(
            ChatCounterMetric.API_REQUEST_COUNT, 1, metric_type=MetricType.COUNTER, endpoint="/api/chat", method="POST"
        )

        try:
            if not self.chat_interface:
                record_metric(
                    ChatCounterMetric.API_ERROR_COUNT,
                    1,
                    metric_type=MetricType.COUNTER,
                    endpoint="/api/chat",
                    status_code="500",
                    error_type="chat_interface_not_initialized",
                )
                raise HTTPException(status_code=500, detail="Chat implementation is not initialized")

            # Convert request context to ChatContext
            chat_context = ChatContext(**request.context)

            # Verify state signature if provided
            if "state" in request.context and "signature" in request.context:
                state = request.context["state"]
                signature = request.context["signature"]
                if not ChatInterface.verify_state(state, signature):
                    logger.warning(f"Invalid state signature received for message {chat_context.message_id}")
                    record_metric(
                        ChatCounterMetric.API_ERROR_COUNT,
                        1,
                        metric_type=MetricType.COUNTER,
                        endpoint="/api/chat",
                        status_code="400",
                        error_type="invalid_state_signature",
                    )
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

            # wrapper function to trace the response generation
            async def chat_response() -> AsyncGenerator[str, None]:
                response_text = ""
                reference_text = ""
                state_update_text = ""

                with trace(
                    message=request.message,
                    history=[msg.model_dump() for msg in request.history],
                    context=chat_context,
                ) as outputs:
                    async for chunk in RagbitsAPI._chat_response_to_sse(response_generator):
                        data_dict = json.loads(chunk[len("data: ") :])

                        content = str(data_dict.get("content", ""))

                        match data_dict.get("type"):
                            case ChatResponseType.TEXT:
                                response_text += content
                            case ChatResponseType.REFERENCE:
                                reference_text += content
                            case ChatResponseType.STATE_UPDATE:
                                state_update_text += content
                            case ChatResponseType.MESSAGE_ID:
                                outputs.message_id = content
                            case ChatResponseType.CONVERSATION_ID:
                                outputs.conversation_id = content

                        yield chunk

                    outputs.response_text = response_text
                    outputs.reference_text = reference_text
                    outputs.state_update_text = state_update_text

            streaming_response = StreamingResponse(
                chat_response(),
                media_type="text/event-stream",
            )

            # Track successful request duration
            duration = time.time() - start_time
            record_metric(
                ChatHistogramMetric.API_REQUEST_DURATION,
                duration,
                metric_type=MetricType.HISTOGRAM,
                endpoint="/api/chat",
                method="POST",
                status="success",
            )

            return streaming_response

        except HTTPException as e:
            # Track HTTP errors
            duration = time.time() - start_time
            record_metric(
                ChatHistogramMetric.API_REQUEST_DURATION,
                duration,
                metric_type=MetricType.HISTOGRAM,
                endpoint="/api/chat",
                method="POST",
                status="error",
            )
            record_metric(
                ChatCounterMetric.API_ERROR_COUNT,
                1,
                metric_type=MetricType.COUNTER,
                endpoint="/api/chat",
                status_code=str(e.status_code),
                error_type="http_exception",
            )
            raise
        except Exception as e:
            # Track unexpected errors
            duration = time.time() - start_time
            record_metric(
                ChatHistogramMetric.API_REQUEST_DURATION,
                duration,
                metric_type=MetricType.HISTOGRAM,
                endpoint="/api/chat",
                method="POST",
                status="error",
            )
            record_metric(
                ChatCounterMetric.API_ERROR_COUNT,
                1,
                metric_type=MetricType.COUNTER,
                endpoint="/api/chat",
                status_code="500",
                error_type=type(e).__name__,
            )
            raise HTTPException(status_code=500, detail="Internal server error") from None

    async def _handle_feedback(self, request: FeedbackRequest) -> JSONResponse:
        """Handle feedback requests with metrics tracking."""
        start_time = time.time()

        # Track API request
        record_metric(
            ChatCounterMetric.API_REQUEST_COUNT,
            1,
            metric_type=MetricType.COUNTER,
            endpoint="/api/feedback",
            method="POST",
        )

        try:
            if not self.chat_interface:
                record_metric(
                    ChatCounterMetric.API_ERROR_COUNT,
                    1,
                    metric_type=MetricType.COUNTER,
                    endpoint="/api/feedback",
                    status_code="500",
                    error_type="chat_interface_not_initialized",
                )
                raise HTTPException(status_code=500, detail="Chat implementation is not initialized")

            await self.chat_interface.save_feedback(
                message_id=request.message_id,
                feedback=request.feedback,
                payload=request.payload,
            )

            # Track successful request duration
            duration = time.time() - start_time
            record_metric(
                ChatHistogramMetric.API_REQUEST_DURATION,
                duration,
                metric_type=MetricType.HISTOGRAM,
                endpoint="/api/feedback",
                method="POST",
                status="success",
            )

            return JSONResponse(content={"status": "success"})

        except HTTPException as e:
            # Track HTTP errors
            duration = time.time() - start_time
            record_metric(
                ChatHistogramMetric.API_REQUEST_DURATION,
                duration,
                metric_type=MetricType.HISTOGRAM,
                endpoint="/api/feedback",
                method="POST",
                status="error",
            )
            record_metric(
                ChatCounterMetric.API_ERROR_COUNT,
                1,
                metric_type=MetricType.COUNTER,
                endpoint="/api/feedback",
                status_code=str(e.status_code),
                error_type="http_exception",
            )
            raise
        except Exception as e:
            # Track unexpected errors
            duration = time.time() - start_time
            record_metric(
                ChatHistogramMetric.API_REQUEST_DURATION,
                duration,
                metric_type=MetricType.HISTOGRAM,
                endpoint="/api/feedback",
                method="POST",
                status="error",
            )
            record_metric(
                ChatCounterMetric.API_ERROR_COUNT,
                1,
                metric_type=MetricType.COUNTER,
                endpoint="/api/feedback",
                status_code="500",
                error_type=type(e).__name__,
            )
            raise HTTPException(status_code=500, detail="Internal server error") from None

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
        chunk_count = 0
        stream_start_time = time.time()

        try:
            async for response in responses:
                chunk_count += 1
                data = json.dumps(
                    {
                        "type": response.type.value,
                        "content": response.content
                        if isinstance(response.content, str | list)
                        else response.content.model_dump(),
                    }
                )
                yield f"data: {data}\n\n"
        finally:
            # Track streaming metrics
            stream_duration = time.time() - stream_start_time
            record_metric(
                ChatHistogramMetric.API_STREAM_DURATION,
                stream_duration,
                metric_type=MetricType.HISTOGRAM,
                endpoint="/api/chat",
            )
            record_metric(
                ChatCounterMetric.API_STREAM_CHUNK_COUNT,
                chunk_count,
                metric_type=MetricType.COUNTER,
                endpoint="/api/chat",
            )

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
