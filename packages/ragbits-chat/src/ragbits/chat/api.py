import importlib
import json
import logging
import re
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, cast

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ragbits.chat.auth import AuthenticationBackend, User
from ragbits.chat.auth.types import LoginRequest, LoginResponse, LogoutRequest
from ragbits.chat.interface import ChatInterface
from ragbits.chat.interface.types import (
    AuthenticationConfig,
    AuthType,
    ChatContext,
    ChatMessageRequest,
    ChatResponseUnion,
    ChunkedContent,
    ConfigResponse,
    FeedbackConfig,
    FeedbackItem,
    FeedbackRequest,
    Image,
    ImageResponse,
)
from ragbits.core.audit.metrics import record_metric
from ragbits.core.audit.metrics.base import MetricType
from ragbits.core.audit.traces import trace

from .metrics import ChatCounterMetric, ChatHistogramMetric

logger = logging.getLogger(__name__)

# Chunk size for large base64 images to prevent SSE message size issues
# Keep chunks extremely small to avoid JSON string length limits in browsers and SSE parsing issues
# Account for JSON overhead: metadata + base64 data should fit comfortably in browser limits
CHUNK_SIZE = 102400  # ~100KB bytes base64 chunks for ultra-safe JSON parsing and SSE transmission


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
        auth_backend: AuthenticationBackend | type[AuthenticationBackend] | str | None = None,
        theme_path: str | None = None,
    ) -> None:
        """
        Initialize the RagbitsAPI.

        Args:
            chat_interface: Either a ChatInterface class (recommended) or a string path to a class
                                in format "module.path:ClassName" (legacy support)
            cors_origins: List of allowed CORS origins. If None, defaults to common development origins.
            ui_build_dir: Path to a custom UI build directory. If None, uses the default package UI.
            debug_mode: Flag enabling debug tools in the default UI
            auth_backend: Authentication backend for user authentication. If None, no authentication required.
            theme_path: Path to a JSON file containing HeroUI theme configuration from heroui.com/themes
        """
        self.chat_interface: ChatInterface = self._load_chat_interface(chat_interface)
        self.dist_dir = Path(ui_build_dir) if ui_build_dir else Path(__file__).parent / "ui-build"
        self.cors_origins = cors_origins or []
        self.debug_mode = debug_mode
        self.auth_backend = self._load_auth_backend(auth_backend)
        self.security = HTTPBearer(auto_error=False) if auth_backend else None
        self.theme_path = Path(theme_path) if theme_path else None

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
        # Authentication routes
        if self.auth_backend:
            # Create security dependency variable to avoid B008 linting error
            security_dependency = Depends(self.security)

            @self.app.post("/api/auth/login", response_class=JSONResponse)
            async def login(request: LoginRequest) -> JSONResponse:
                return await self._handle_login(request)

            @self.app.post("/api/auth/logout", response_class=JSONResponse)
            async def logout(request: LogoutRequest) -> JSONResponse:
                return await self._handle_logout(request)

            @self.app.post("/api/chat", response_class=StreamingResponse)
            async def chat_message(
                request: ChatMessageRequest,
                credentials: HTTPAuthorizationCredentials | None = security_dependency,
            ) -> StreamingResponse:
                return await self._handle_chat_message(request, credentials)

            @self.app.post("/api/feedback", response_class=JSONResponse)
            async def feedback(
                request: FeedbackRequest,
                credentials: HTTPAuthorizationCredentials | None = security_dependency,
            ) -> JSONResponse:
                return await self._handle_feedback(request, credentials)
        else:

            @self.app.post("/api/chat", response_class=StreamingResponse)
            async def chat_message(
                request: ChatMessageRequest,
            ) -> StreamingResponse:
                return await self._handle_chat_message(request, None)

            @self.app.post("/api/feedback", response_class=JSONResponse)
            async def feedback(
                request: FeedbackRequest,
            ) -> JSONResponse:
                return await self._handle_feedback(request, None)

        @self.app.get("/api/config", response_class=JSONResponse)
        async def config() -> JSONResponse:
            feedback_config = self.chat_interface.feedback_config

            config_response = ConfigResponse(
                feedback=FeedbackConfig(
                    like=FeedbackItem(
                        enabled=feedback_config.like_enabled,
                        form=feedback_config.like_form,
                    ),
                    dislike=FeedbackItem(
                        enabled=feedback_config.dislike_enabled,
                        form=feedback_config.dislike_form,
                    ),
                ),
                customization=self.chat_interface.ui_customization,
                user_settings=self.chat_interface.user_settings,
                debug_mode=self.debug_mode,
                conversation_history=self.chat_interface.conversation_history,
                show_usage=self.chat_interface.show_usage,
                authentication=AuthenticationConfig(
                    enabled=self.auth_backend is not None,
                    auth_types=[AuthType.CREDENTIALS],
                ),
            )

            return JSONResponse(content=config_response.model_dump())

        # Theme CSS endpoint - always available, returns 404 if no theme configured
        @self.app.get("/api/theme", response_class=PlainTextResponse)
        async def theme() -> PlainTextResponse:
            if not self.theme_path or not self.theme_path.exists():
                raise HTTPException(status_code=404, detail="No theme configured")

            try:
                with open(self.theme_path, encoding="utf-8") as f:
                    json_content = f.read().strip()

                css_content = RagbitsAPI._convert_heroui_json_to_css(json_content)

                return PlainTextResponse(
                    content=css_content, media_type="text/css", headers={"Cache-Control": "public, max-age=3600"}
                )
            except Exception as e:
                logger.error(f"Error serving theme: {e}")
                raise HTTPException(status_code=500, detail="Error loading theme") from e

        @self.app.get("/{full_path:path}", response_class=HTMLResponse)
        async def root() -> HTMLResponse:
            index_file = self.dist_dir / "index.html"
            with open(str(index_file)) as file:
                return HTMLResponse(content=file.read())

    async def _validate_authentication(self, credentials: HTTPAuthorizationCredentials | None) -> User | None:
        """Validate authentication credentials and return user if valid."""
        if not self.auth_backend:
            return None

        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # The jwt_token should be the session_id
        auth_result = await self.auth_backend.validate_token(credentials.credentials)
        if not auth_result.success:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=auth_result.error_message or "Invalid session",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return auth_result.user

    @staticmethod
    def _prepare_chat_context(
        request: ChatMessageRequest,
        authenticated_user: User | None,
        credentials: HTTPAuthorizationCredentials | None,
    ) -> ChatContext:
        """Prepare and validate chat context from request."""
        chat_context = ChatContext(**request.context)

        # Add session_id to context if authenticated
        if authenticated_user and credentials:
            chat_context.session_id = credentials.credentials
            chat_context.user = authenticated_user

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

        return chat_context

    async def _handle_chat_message(
        self, request: ChatMessageRequest, credentials: HTTPAuthorizationCredentials | None = None
    ) -> StreamingResponse:  # noqa: PLR0915
        """Handle chat message requests with metrics tracking."""
        start_time = time.time()

        # Track API request
        record_metric(
            ChatCounterMetric.API_REQUEST_COUNT, 1, metric_type=MetricType.COUNTER, endpoint="/api/chat", method="POST"
        )

        try:
            # Validate authentication if required
            authenticated_user = await self._validate_authentication(credentials)

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

            # Prepare chat context
            chat_context = RagbitsAPI._prepare_chat_context(request, authenticated_user, credentials)

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
                            case "text":
                                response_text += content
                            case "reference":
                                reference_text += content
                            case "state_update":
                                state_update_text += content
                            case "message_id":
                                outputs.message_id = content
                            case "conversation_id":
                                outputs.conversation_id = content
                            case "image":
                                outputs.image_url = content

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

    async def _handle_feedback(
        self, request: FeedbackRequest, credentials: HTTPAuthorizationCredentials | None = None
    ) -> JSONResponse:
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
            # Validate authentication if required
            await self._validate_authentication(credentials)

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

    async def _handle_login(self, request: LoginRequest) -> JSONResponse:
        """Handle user login requests."""
        if not self.auth_backend:
            raise HTTPException(status_code=500, detail="Authentication not configured")

        try:
            from .auth.types import UserCredentials

            credentials = UserCredentials(username=request.username, password=request.password)
            auth_result = await self.auth_backend.authenticate_with_credentials(credentials)

            if auth_result.success and auth_result.jwt_token:
                return JSONResponse(
                    content=LoginResponse(
                        success=True,
                        user=auth_result.user if auth_result.user else None,
                        error_message=None,
                        jwt_token=auth_result.jwt_token,
                    ).model_dump()
                )
            else:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content=LoginResponse(
                        success=False,
                        user=None,
                        error_message=auth_result.error_message or "Invalid credentials",
                        jwt_token=None,
                    ).model_dump(),
                )
        except Exception as e:
            logger.error(f"Login error: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=LoginResponse(
                    success=False,
                    user=None,
                    error_message="Internal server error",
                    jwt_token=None,
                ).model_dump(),
            )

    async def _handle_logout(self, request: LogoutRequest) -> JSONResponse:
        """Handle user logout requests."""
        if not self.auth_backend:
            raise HTTPException(status_code=500, detail="Authentication not configured")

        try:
            success = await self.auth_backend.revoke_token(request.token)
            return JSONResponse(content={"success": success})
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"success": False, "error_message": "Internal server error"},
            )

    @staticmethod
    async def _chat_response_to_sse(
        responses: AsyncGenerator[ChatResponseUnion],
    ) -> AsyncGenerator[str, None]:
        """
        Formats chat responses into Server-Sent Events (SSE) format for streaming to the client.
        Each response is converted to JSON and wrapped in the SSE 'data:' prefix.
        Automatically chunks large base64 images to prevent SSE message size issues.

        Args:
            responses: The chat response generator
        """
        chunk_count = 0
        stream_start_time = time.time()

        try:
            async for response in responses:
                chunk_count += 1
                response_to_send: Any = response.content
                if isinstance(response.content, dict):
                    response_to_send = {
                        key: model.model_dump() if isinstance(model, BaseModel) else model
                        for key, model in response.content.items()
                    }

                # Auto-chunk large images using ChunkedContent model
                if isinstance(response, ImageResponse) and cast(Image, response.content).url.startswith("data:"):
                    # Auto-chunk the image
                    async for chunk_response in RagbitsAPI._create_chunked_responses(response):
                        yield f"data: {json.dumps(chunk_response)}\n\n"

                    continue  # Skip normal processing for chunked images

                # Normal processing for:
                # - Non-image responses
                # - Regular URL images (https://..., http://..., /path/to/image.jpg)
                data = json.dumps(
                    {
                        "type": response.get_type(),
                        "content": response_to_send.model_dump()
                        if isinstance(response_to_send, BaseModel)
                        else response_to_send,
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
    async def _create_chunked_responses(base64_response: ImageResponse) -> AsyncGenerator[dict, None]:
        """Create chunked responses from a base64 response."""
        image_content = cast(Image, base64_response.content)
        mime_type, base64_data = image_content.url.split(",", 1)

        chunks = [base64_data[i : i + CHUNK_SIZE] for i in range(0, len(base64_data), CHUNK_SIZE)]

        for i, chunk in enumerate(chunks):
            chunked_content = ChunkedContent(
                id=image_content.id,
                content_type="image",
                chunk_index=i,
                total_chunks=len(chunks),
                mime_type=mime_type,
                data=chunk,
            )

            yield {"type": "chunked_content", "content": chunked_content.model_dump()}

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

    @staticmethod
    def _load_auth_backend(
        implementation: AuthenticationBackend | type[AuthenticationBackend] | str | None,
    ) -> AuthenticationBackend | None:
        """Initialize the auth backend from a class, instance, or module path.

        Args:
            implementation: Either an AuthenticationBackend instance, class, or a
            string path in format "module:class" or "module:function"
        """
        if implementation is None:
            return None

        # If it's already an instance, return it directly
        if isinstance(implementation, AuthenticationBackend):
            logger.info(f"Using existing auth backend instance: {type(implementation).__name__}")
            return implementation

        if isinstance(implementation, str):
            module_stringify, object_stringify = implementation.split(":")
            logger.info(f"Loading Auth implementation from path: {module_stringify}, object: {object_stringify}")

            module = importlib.import_module(module_stringify)
            implementation_obj = getattr(module, object_stringify)

            # If it's a function, call it to get the backend instance
            if callable(implementation_obj) and not isinstance(implementation_obj, type):
                logger.info(f"Calling factory function: {object_stringify}")
                return implementation_obj()
            else:
                implementation_class = implementation_obj
        else:
            implementation_class = implementation

        if not issubclass(implementation_class, AuthenticationBackend):
            raise TypeError("Implementation must inherit from AuthenticationBackend")

        logger.info(f"Initialized auth backend: {implementation_class.__name__}")
        return implementation_class()

    def run(self, host: str = "127.0.0.1", port: int = 8000) -> None:
        """
        Used for starting the API
        """
        uvicorn.run(self.app, host=host, port=port)

    @staticmethod
    def _convert_heroui_json_to_css(json_content: str) -> str:
        """Convert HeroUI JSON theme configuration to CSS variables."""
        try:
            theme_config = json.loads(json_content)
            css_lines = [
                "/* Auto-generated CSS from HeroUI theme configuration */",
                "",
                ":root {",
            ]

            # Process light theme
            if "themes" in theme_config and "light" in theme_config["themes"]:
                light_colors = theme_config["themes"]["light"]["colors"]
                css_lines.extend(RagbitsAPI._process_theme_colors(light_colors))

            # Add layout properties
            if "layout" in theme_config:
                for prop, value in theme_config["layout"].items():
                    css_prop = re.sub(r"([A-Z])", r"-\1", prop).lower()
                    css_lines.append(f"  --heroui-{css_prop}: {value};")

            css_lines.append("}")
            css_lines.append("")

            # Process dark theme
            if "themes" in theme_config and "dark" in theme_config["themes"]:
                css_lines.append(".dark {")
                dark_colors = theme_config["themes"]["dark"]["colors"]
                css_lines.extend(RagbitsAPI._process_theme_colors(dark_colors))

                if "layout" in theme_config:
                    for prop, value in theme_config["layout"].items():
                        css_prop = re.sub(r"([A-Z])", r"-\1", prop).lower()
                        css_lines.append(f"  --heroui-{css_prop}: {value};")

                css_lines.append("}")

            # Add body styling
            css_lines.extend(
                [
                    "",
                    "body {",
                    "  background-color: var(--heroui-background);",
                    "  color: var(--heroui-foreground);",
                    "}",
                ]
            )

            return "\n".join(css_lines)

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in theme file: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON theme file") from e
        except Exception as e:
            logger.error(f"Error converting theme: {e}")
            raise HTTPException(status_code=500, detail="Error processing theme") from e

    @staticmethod
    def _process_theme_colors(colors: dict) -> list[str]:
        """Process theme colors and return CSS variable declarations."""
        css_lines = []

        for color_name, color_value in colors.items():
            if isinstance(color_value, dict):
                for shade, value in color_value.items():
                    if shade == "DEFAULT":
                        css_lines.append(f"  --heroui-{color_name}: {value};")
                    elif isinstance(value, str):
                        css_lines.append(f"  --heroui-{color_name}-{shade}: {value};")
            elif isinstance(color_value, str):
                css_lines.append(f"  --heroui-{color_name}: {color_value};")

        return css_lines
