import asyncio
import importlib
import json
import logging
import re
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Any, cast

import uvicorn
from fastapi import FastAPI, HTTPException, Request, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ragbits.chat.auth import AuthenticationBackend, User
from ragbits.chat.auth.backends import MultiAuthenticationBackend, OAuth2AuthenticationBackend
from ragbits.chat.auth.provider_config import get_provider_visual_config
from ragbits.chat.auth.types import LoginRequest, LoginResponse, OAuth2Credentials
from ragbits.chat.config import BASE_URL, CHUNK_SIZE, IS_PRODUCTION, SESSION_COOKIE_NAME
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
    OAuth2ProviderConfig,
)
from ragbits.core.audit.metrics import record_metric
from ragbits.core.audit.metrics.base import MetricType
from ragbits.core.audit.traces import trace

from .metrics import ChatCounterMetric, ChatHistogramMetric

logger = logging.getLogger(__name__)


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
        self.theme_path = Path(theme_path) if theme_path else None

        self.frontend_base_url = BASE_URL

        @asynccontextmanager
        async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
            await self.chat_interface.setup()

            # Start background cleanup tasks for session and OAuth state management
            cleanup_tasks: list[asyncio.Task] = []

            if self.auth_backend:
                cleanup_tasks.append(asyncio.create_task(self._session_cleanup_loop()))
                cleanup_tasks.append(asyncio.create_task(self._oauth_state_cleanup_loop()))

            yield

            # Cancel all cleanup tasks on shutdown
            for task in cleanup_tasks:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

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

    def setup_routes(self) -> None:  # noqa: PLR0915
        """Defines API routes."""
        # Authentication routes
        if self.auth_backend:

            @self.app.post("/api/auth/login", response_class=JSONResponse)
            async def login(request: LoginRequest) -> JSONResponse:
                return await self._handle_login(request)

            @self.app.post("/api/auth/logout", response_class=JSONResponse)
            async def logout(request: Request) -> JSONResponse:
                return await self._handle_logout(request)

            # OAuth2 routes (if OAuth2 backend is configured)
            oauth2_backends = []
            if isinstance(self.auth_backend, MultiAuthenticationBackend):
                oauth2_backends = self.auth_backend.get_oauth2_backends()
            elif isinstance(self.auth_backend, OAuth2AuthenticationBackend):
                oauth2_backends = [self.auth_backend]

            if oauth2_backends:
                # Create a mapping of provider name to backend for quick lookup
                oauth2_backend_map = {backend.provider.name: backend for backend in oauth2_backends}

                @self.app.get("/api/auth/authorize/{provider}", response_class=JSONResponse)
                async def oauth2_authorize(provider: str) -> JSONResponse:
                    """Generate OAuth2 authorization URL for specified provider."""
                    backend = oauth2_backend_map.get(provider)
                    if not backend:
                        raise HTTPException(status_code=404, detail=f"OAuth2 provider '{provider}' not found")

                    authorize_url, state = backend.generate_authorize_url()
                    return JSONResponse(content={"authorize_url": authorize_url, "state": state})

                @self.app.get("/api/auth/callback/{provider}", response_class=RedirectResponse)
                async def oauth2_callback(
                    provider: str, code: str | None = None, state: str | None = None
                ) -> RedirectResponse:
                    """Handle OAuth2 callback from provider."""
                    backend = oauth2_backend_map.get(provider)
                    if not backend:
                        raise HTTPException(status_code=404, detail=f"OAuth2 provider '{provider}' not found")

                    return await self._handle_oauth2_callback(code, state, backend)

        @self.app.post("/api/chat", response_class=StreamingResponse)
        async def chat_message(
            request: Request,
            chat_request: ChatMessageRequest,
        ) -> StreamingResponse:
            return await self._handle_chat_message(chat_request, request)

        @self.app.post("/api/feedback", response_class=JSONResponse)
        async def feedback(
            request: Request,
            feedback_request: FeedbackRequest,
        ) -> JSONResponse:
            return await self._handle_feedback(feedback_request, request)

        @self.app.post("/api/upload", response_class=JSONResponse)
        async def upload_file(file: UploadFile) -> JSONResponse:
            return await self._handle_file_upload(file)

        @self.app.get("/api/config", response_class=JSONResponse)
        async def config() -> JSONResponse:
            feedback_config = self.chat_interface.feedback_config

            # Determine available auth types and OAuth2 providers based on backend
            auth_types = []
            oauth2_providers = []

            if self.auth_backend:
                if isinstance(self.auth_backend, MultiAuthenticationBackend):
                    # Multi backend: check what types are available
                    if self.auth_backend.get_credentials_backends():
                        auth_types.append(AuthType.CREDENTIALS)

                    oauth2_backends = self.auth_backend.get_oauth2_backends()
                    if oauth2_backends:
                        auth_types.append(AuthType.OAUTH2)
                        for backend in oauth2_backends:
                            visual_config = get_provider_visual_config(backend.provider.name)
                            oauth2_providers.append(
                                OAuth2ProviderConfig(
                                    name=backend.provider.name,
                                    display_name=backend.provider.display_name,
                                    color=visual_config.color,
                                    button_color=visual_config.button_color,
                                    text_color=visual_config.text_color,
                                    icon_svg=visual_config.icon_svg,
                                )
                            )
                elif isinstance(self.auth_backend, OAuth2AuthenticationBackend):
                    # Single OAuth2 backend
                    auth_types = [AuthType.OAUTH2]
                    visual_config = get_provider_visual_config(self.auth_backend.provider.name)
                    oauth2_providers = [
                        OAuth2ProviderConfig(
                            name=self.auth_backend.provider.name,
                            display_name=self.auth_backend.provider.display_name,
                            color=visual_config.color,
                            button_color=visual_config.button_color,
                            text_color=visual_config.text_color,
                            icon_svg=visual_config.icon_svg,
                        )
                    ]
                else:
                    # Single credentials backend
                    auth_types = [AuthType.CREDENTIALS]

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
                    auth_types=auth_types,
                    oauth2_providers=oauth2_providers,
                ),
                supports_upload=self.chat_interface.upload_handler is not None,
            )

            return JSONResponse(content=config_response.model_dump())

        # User info endpoint - returns current authenticated user
        @self.app.get("/api/user", response_class=JSONResponse)
        async def get_user(request: Request) -> JSONResponse:
            """Get current authenticated user from session cookie."""
            user = await self.get_current_user_from_cookie(request)
            if user:
                return JSONResponse(content=user.model_dump())
            return JSONResponse(content=None, status_code=401)

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

    @staticmethod
    def _prepare_chat_context(
        request: ChatMessageRequest,
        authenticated_user: User | None,
        session_id: str | None,
    ) -> ChatContext:
        """Prepare and validate chat context from request."""
        chat_context = ChatContext(**request.context)

        # Add session_id to context if authenticated
        if authenticated_user and session_id:
            chat_context.session_id = session_id
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

    async def _handle_chat_message(self, chat_request: ChatMessageRequest, request: Request) -> StreamingResponse:  # noqa: PLR0915
        """Handle chat message requests with metrics tracking."""
        start_time = time.time()

        # Track API request
        record_metric(
            ChatCounterMetric.API_REQUEST_COUNT, 1, metric_type=MetricType.COUNTER, endpoint="/api/chat", method="POST"
        )

        try:
            # Validate authentication if required using cookies
            authenticated_user = await self.require_authenticated_user(request)

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
            session_id = request.cookies.get(SESSION_COOKIE_NAME)
            chat_context = RagbitsAPI._prepare_chat_context(chat_request, authenticated_user, session_id)

            # Get the response generator from the chat interface
            response_generator = self.chat_interface.chat(
                message=chat_request.message,
                history=[msg.model_dump() for msg in chat_request.history],
                context=chat_context,
            )

            # wrapper function to trace the response generation
            async def chat_response() -> AsyncGenerator[str, None]:
                response_text = ""
                reference_text = ""
                state_update_text = ""

                with trace(
                    message=chat_request.message,
                    history=[msg.model_dump() for msg in chat_request.history],
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

    async def _handle_feedback(self, feedback_request: FeedbackRequest, request: Request) -> JSONResponse:
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
            # Validate authentication if required using cookies
            await self.require_authenticated_user(request)

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
                message_id=feedback_request.message_id,
                feedback=feedback_request.feedback,
                payload=feedback_request.payload,
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

    async def _handle_file_upload(self, file: UploadFile) -> JSONResponse:
        """
        Handle file upload requests.

        Args:
            file: The uploaded file.

        Returns:
            JSONResponse with status.
        """
        if self.chat_interface.upload_handler is None:
            raise HTTPException(status_code=400, detail="File upload not supported")

        try:
            # Check if handler is async and call it
            if asyncio.iscoroutinefunction(self.chat_interface.upload_handler):
                await self.chat_interface.upload_handler(file)
            else:
                await asyncio.to_thread(self.chat_interface.upload_handler, file)

            return JSONResponse(content={"status": "success", "filename": file.filename})
        except Exception as e:
            logger.error(f"File upload error: {e}")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def get_current_user_from_cookie(self, request: Request) -> User | None:
        """
        Get current user from session cookie.

        Args:
            request: FastAPI request object

        Returns:
            User object if authenticated, None otherwise
        """
        if not self.auth_backend:
            return None

        session_id = request.cookies.get(SESSION_COOKIE_NAME)
        if not session_id:
            return None

        result = await self.auth_backend.validate_session(session_id)
        if result.success:
            return result.user

        return None

    async def require_authenticated_user(self, request: Request) -> User | None:
        """
        Get current user from session cookie and raise HTTPException if authentication
        is required but user is not authenticated.

        This is a reusable dependency for handlers that require authentication.

        Args:
            request: FastAPI request object

        Returns:
            User object if authenticated (or if no auth is required), None if no auth backend

        Raises:
            HTTPException: 401 Unauthorized if authentication is required but user is not authenticated
        """
        authenticated_user = await self.get_current_user_from_cookie(request)
        if self.auth_backend and not authenticated_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        return authenticated_user

    def get_session_expiry_seconds(self) -> int:
        """
        Get session expiry time in seconds from the auth backend configuration.

        Returns:
            Session expiry time in seconds (default: 24 hours if not configured)
        """
        # Default to 24 hours
        default_expiry_hours = 24

        if not self.auth_backend:
            return default_expiry_hours * 3600

        # Check if the backend has session_expiry_hours attribute
        if hasattr(self.auth_backend, "session_expiry_hours"):
            return self.auth_backend.session_expiry_hours * 3600

        # For MultiAuthenticationBackend, try to get from first backend that has it
        if isinstance(self.auth_backend, MultiAuthenticationBackend):
            for backend in self.auth_backend.backends:
                if hasattr(backend, "session_expiry_hours"):
                    return backend.session_expiry_hours * 3600

        return default_expiry_hours * 3600

    async def _handle_login(self, request: LoginRequest) -> JSONResponse:
        """Handle user login requests with credentials."""
        if not self.auth_backend:
            raise HTTPException(status_code=500, detail="Authentication not configured")

        try:
            # LoginRequest is UserCredentials
            auth_result = await self.auth_backend.authenticate_with_credentials(request)

            if auth_result.success and auth_result.session_id:
                response = JSONResponse(
                    content=LoginResponse(
                        success=True,
                        user=auth_result.user if auth_result.user else None,
                        error_message=None,
                    ).model_dump()
                )

                # Set secure HTTP-only cookie using backend's session expiry configuration
                session_expiry_seconds = self.get_session_expiry_seconds()
                response.set_cookie(
                    key=SESSION_COOKIE_NAME,
                    value=auth_result.session_id,
                    httponly=True,
                    secure=IS_PRODUCTION,  # Only require HTTPS in production
                    samesite="lax",
                    max_age=session_expiry_seconds,
                    path="/",
                )

                return response
            else:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content=LoginResponse(
                        success=False,
                        user=None,
                        error_message=auth_result.error_message or "Invalid credentials",
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
                ).model_dump(),
            )

    async def _handle_logout(self, request: Request) -> JSONResponse:
        """Handle user logout requests."""
        if not self.auth_backend:
            raise HTTPException(status_code=500, detail="Authentication not configured")

        try:
            # Get session ID from cookie
            session_id = request.cookies.get(SESSION_COOKIE_NAME)

            if not session_id:
                # No session cookie, just return success
                response = JSONResponse(content={"success": True})
                response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
                return response

            # Delete the session from store
            success = await self.auth_backend.revoke_session(session_id)

            response = JSONResponse(content={"success": success})
            # Clear the session cookie
            response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
            return response

        except Exception as e:
            logger.error(f"Logout error: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"success": False, "error": "Internal server error"},
            )

    async def _handle_oauth2_callback(  # noqa: PLR6301
        self, code: str | None, state: str | None, backend: OAuth2AuthenticationBackend
    ) -> RedirectResponse:
        """
        Handle OAuth2 callback from provider.

        This endpoint receives the authorization code from the OAuth2 provider,
        exchanges it for an access token, authenticates the user, creates a session,
        and redirects to the frontend with a secure HTTP-only cookie.

        Args:
            code: Authorization code from OAuth2 provider
            state: CSRF protection state parameter
            backend: The specific OAuth2 backend for this provider
        """
        # Verify required parameters
        if not code:
            # Redirect to login with error
            return RedirectResponse(url=f"{self.frontend_base_url}/login?error=missing_code", status_code=302)

        # Verify state parameter for CSRF protection
        if not state or not backend.verify_state(state):
            return RedirectResponse(url=f"{self.frontend_base_url}/login?error=invalid_state", status_code=302)

        try:
            # Exchange code for access token
            access_token = await backend.exchange_code_for_token(code)
            if not access_token:
                return RedirectResponse(
                    url=f"{self.frontend_base_url}/login?error=token_exchange_failed", status_code=302
                )

            # Authenticate with the access token
            oauth_credentials = OAuth2Credentials(access_token=access_token, token_type="Bearer")  # noqa: S106
            auth_result = await backend.authenticate_with_oauth2(oauth_credentials)

            if not auth_result.success or not auth_result.session_id:
                error_msg = auth_result.error_message or "Authentication failed"
                return RedirectResponse(url=f"{self.frontend_base_url}/login?error={error_msg}", status_code=302)

            # Success! Create redirect response with session cookie
            response = RedirectResponse(url=f"{self.frontend_base_url}/", status_code=302)

            # Set secure HTTP-only cookie
            session_expiry_seconds = backend.session_expiry_hours * 3600
            response.set_cookie(
                key=SESSION_COOKIE_NAME,
                value=auth_result.session_id,
                httponly=True,
                secure=IS_PRODUCTION,  # Only require HTTPS in production
                samesite="lax",
                max_age=session_expiry_seconds,
                path="/",
            )

            return response

        except Exception as e:
            logger.error(f"OAuth2 callback error: {e}")
            return RedirectResponse(url=f"{self.frontend_base_url}/login?error=internal_error", status_code=302)

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

    async def _session_cleanup_loop(self) -> None:
        if (
            not self.auth_backend
            or not hasattr(self.auth_backend, "session_store")
            or not hasattr(self.auth_backend.session_store, "cleanup_expired_sessions")
        ):
            return

        while True:
            await asyncio.sleep(3600)  # Run every hour
            try:
                removed = self.auth_backend.session_store.cleanup_expired_sessions()  # type: ignore
                if removed > 0:
                    logger.info(f"Cleaned up {removed} expired sessions")
            except Exception as e:
                logger.exception(f"Error during session cleanup: {e}")

    async def _oauth_state_cleanup_loop(self) -> None:
        oauth2_backends = []
        if isinstance(self.auth_backend, MultiAuthenticationBackend):
            oauth2_backends = self.auth_backend.get_oauth2_backends()
        elif isinstance(self.auth_backend, OAuth2AuthenticationBackend):
            oauth2_backends = [self.auth_backend]

        if not oauth2_backends:
            return

        while True:
            await asyncio.sleep(600)  # Run every 10 minutes
            try:
                total_removed = 0
                for backend in oauth2_backends:
                    removed = backend.cleanup_expired_states()
                    total_removed += removed
                if total_removed > 0:
                    logger.info(f"Cleaned up {total_removed} expired OAuth2 state tokens")
            except Exception as e:
                logger.exception(f"Error during OAuth state cleanup: {e}")
