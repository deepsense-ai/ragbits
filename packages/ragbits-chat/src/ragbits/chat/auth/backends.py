import secrets
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any, cast
from urllib.parse import urlencode

import bcrypt
import httpx
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError

from ragbits.chat.auth.base import AuthenticationBackend, AuthenticationResponse, AuthOptions
from ragbits.chat.auth.types import JWTToken, OAuth2Credentials, User, UserCredentials
from ragbits.core.utils import get_secret_key


class ListAuthenticationBackend(AuthenticationBackend):
    """Authentication backend using a predefined list of users."""

    def __init__(
        self,
        users: list[dict[str, Any]],
        default_options: AuthOptions | None = None,
    ):
        """
        Initialize with a list of user dictionaries.

        Args:
            users: List of user dicts with 'username', 'password', and optional fields
            jwt_secret: Secret key for JWT jwt_token signing (generates random if not provided)
            default_options: Default options for the component
        """
        if default_options is None:
            default_options = AuthOptions()
        super().__init__(default_options)
        self.users = {}
        self.jwt_secret = get_secret_key()
        self.jwt_algorithm = default_options.jwt_algorithm
        self.token_expiry_minutes = default_options.token_expiry_minutes
        self.revoked_tokens: set[str] = set()  # Blacklist for revoked tokens

        for user_data in users:
            # Hash passwords with bcrypt for security
            password_hash = bcrypt.hashpw(user_data["password"].encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            self.users[user_data["username"]] = {
                "password_hash": password_hash,
                "user": User(
                    user_id=user_data.get("user_id", str(uuid.uuid4())),
                    username=user_data["username"],
                    email=user_data.get("email"),
                    full_name=user_data.get("full_name"),
                    roles=user_data.get("roles", []),
                    metadata=user_data.get("metadata", {}),
                ),
            }

    async def authenticate_with_credentials(self, credentials: UserCredentials) -> AuthenticationResponse:  # noqa: PLR6301
        """
        Authenticate into backend using provided credentials

        Args:
            credentials: User credentials
        Returns:
            AuthenticationResponse: Result of authentication
        """
        user_data = self.users.get(credentials.username)
        if not user_data:
            return AuthenticationResponse(success=False, error_message="User not found")

        # Verify password with bcrypt
        password_hash = str(user_data["password_hash"])
        if not bcrypt.checkpw(credentials.password.encode("utf-8"), password_hash.encode("utf-8")):
            return AuthenticationResponse(success=False, error_message="Invalid password")

        user = cast(User, user_data["user"])

        # Create JWT jwt_token
        jwt_token = self._create_jwt_token(user)

        return AuthenticationResponse(success=True, user=user, jwt_token=jwt_token)

    def _create_jwt_token(self, user: User) -> JWTToken:
        """Create a JWT jwt_token for the user."""
        now = datetime.now(timezone.utc)
        expires_in = self.token_expiry_minutes * 60  # Convert to seconds

        payload = {
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "roles": user.roles,
            "metadata": user.metadata,
            "iat": now,
            "exp": now + timedelta(minutes=self.token_expiry_minutes),
        }

        access_token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

        token_type = "bearer"  # noqa: S105
        return JWTToken(access_token=access_token, token_type=token_type, expires_in=expires_in, user=user)

    async def validate_token(self, token: str) -> AuthenticationResponse:
        """Validate a JWT jwt_token."""
        # Check if token is blacklisted (revoked)
        if token in self.revoked_tokens:
            return AuthenticationResponse(success=False, error_message="Token has been revoked")

        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])

            # Reconstruct user from jwt_token payload
            user = User(
                user_id=payload["user_id"],
                username=payload["username"],
                email=payload.get("email"),
                full_name=payload.get("full_name"),
                roles=payload.get("roles", []),
                metadata=payload.get("metadata", {}),
            )

            return AuthenticationResponse(success=True, user=user)

        except ExpiredSignatureError:
            return AuthenticationResponse(success=False, error_message="Token expired")
        except JWTError:
            return AuthenticationResponse(success=False, error_message="Invalid jwt_token")

    async def authenticate_with_oauth2(self, oauth_credentials: OAuth2Credentials) -> AuthenticationResponse:  # noqa: PLR6301
        """
        Authenticate user with OAuth2 credentials.

        Args:
            oauth_credentials: OAuth2 credentials

        Returns:
            AuthenticationResponse: Authentication failure as OAuth2 is not supported
        """
        return AuthenticationResponse(success=False, error_message="OAuth2 not supported by ListAuthentication")

    async def revoke_token(self, token: str) -> bool:  # noqa: PLR6301
        """
        Revoke a JWT token.

        Args:
            token: The JWT token to revoke

        Raises:
            NotImplementedError: This method is not implemented
        """
        raise NotImplementedError(
            "ListAuthenticationBackend is designed to run in development / testing scenarios. "
            "Revoking tokens is not implemented in this backend, "
            "if you need to revoke tokens please consider using different backend or implementing your own."
        )

    def cleanup_expired_tokens(self) -> int:
        """
        Remove expired tokens from the blacklist to prevent memory bloat.

        Returns:
            Number of tokens removed
        """
        tokens_to_remove = []

        for token in self.revoked_tokens:
            try:
                # Try to decode the token - if it raises ExpiredSignatureError, it's expired
                jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            except ExpiredSignatureError:
                # Token is expired, safe to remove from blacklist
                tokens_to_remove.append(token)
            except JWTError:
                # Token is invalid, remove it too
                tokens_to_remove.append(token)

        for token in tokens_to_remove:
            self.revoked_tokens.remove(token)

        return len(tokens_to_remove)


class OAuth2Provider(ABC):
    """Abstract base class for OAuth2 providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'discord')."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Provider display name (e.g., 'Discord')."""
        pass

    @property
    @abstractmethod
    def authorize_url(self) -> str:
        """OAuth2 authorization endpoint."""
        pass

    @property
    @abstractmethod
    def token_url(self) -> str:
        """OAuth2 token exchange endpoint."""
        pass

    @property
    @abstractmethod
    def user_info_url(self) -> str:
        """User info endpoint."""
        pass

    @property
    @abstractmethod
    def scope(self) -> str:
        """OAuth2 scopes to request."""
        pass

    @abstractmethod
    def create_user_from_data(self, user_data: dict[str, Any]) -> User:
        """
        Create a User object from provider-specific user data.

        Args:
            user_data: Raw user data from the provider

        Returns:
            User object
        """
        pass


class DiscordOAuth2Provider(OAuth2Provider):
    """Discord OAuth2 provider implementation."""

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "discord"

    @property
    def display_name(self) -> str:
        """Return the provider display name."""
        return "Discord"

    @property
    def authorize_url(self) -> str:
        """Return the OAuth2 authorization URL."""
        return "https://discord.com/api/oauth2/authorize"

    @property
    def token_url(self) -> str:
        """Return the OAuth2 token exchange URL."""
        return "https://discord.com/api/oauth2/token"

    @property
    def user_info_url(self) -> str:
        """Return the user info API URL."""
        return "https://discord.com/api/users/@me"

    @property
    def scope(self) -> str:
        """Return the OAuth2 scope to request."""
        return "identify email"

    def create_user_from_data(self, user_data: dict[str, Any]) -> User:  # noqa: PLR6301
        """Create User object from Discord data."""
        return User(
            user_id=f"discord_{user_data['id']}",
            username=user_data.get("username", ""),
            email=user_data.get("email"),
            full_name=user_data.get("global_name"),
            roles=["user"],
            metadata={
                "provider": "discord",
                "avatar": user_data.get("avatar"),
                "discriminator": user_data.get("discriminator"),
            },
        )


class OAuth2AuthenticationBackend(AuthenticationBackend):
    """Generic OAuth2 authentication backend supporting multiple providers."""

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        redirect_uri: str | None = None,
        provider: OAuth2Provider | None = None,
        default_options: AuthOptions | None = None,
    ):
        """
        Initialize OAuth2 authentication backend.

        Args:
            client_id: OAuth2 client ID (or set DISCORD_CLIENT_ID env var)
            client_secret: OAuth2 client secret (or set DISCORD_CLIENT_SECRET env var)
            redirect_uri: Callback URL for OAuth2 flow (or set OAUTH2_REDIRECT_URI env var,
                         defaults to 'http://localhost:8000/api/auth/callback/{provider_name}')
            provider: OAuth2 provider implementation (defaults to Discord)
            default_options: Default options for the component

        Note:
            The default redirect_uri uses a provider-specific path for better isolation and debugging.
            For Discord, it defaults to: http://localhost:8000/api/auth/callback/discord
        """
        import os

        if default_options is None:
            default_options = AuthOptions()
        super().__init__(default_options)

        self.provider = provider or DiscordOAuth2Provider()

        # Get credentials from args or environment variables
        self.client_id = client_id or os.getenv(f"{self.provider.name.upper()}_CLIENT_ID")
        self.client_secret = client_secret or os.getenv(f"{self.provider.name.upper()}_CLIENT_SECRET")

        # Use provider-specific callback URL for better isolation and debugging
        default_redirect_uri = f"http://localhost:8000/api/auth/callback/{self.provider.name}"
        self.redirect_uri = redirect_uri or os.getenv("OAUTH2_REDIRECT_URI") or default_redirect_uri

        if not self.client_id or not self.client_secret:
            raise ValueError(
                f"OAuth2 credentials not provided. Either pass client_id and client_secret to the constructor, "
                f"or set {self.provider.name.upper()}_CLIENT_ID and {self.provider.name.upper()}_CLIENT_SECRET "
                f"environment variables."
            )

        self.jwt_secret = get_secret_key()
        self.jwt_algorithm = default_options.jwt_algorithm
        self.token_expiry_minutes = default_options.token_expiry_minutes

        # State storage for CSRF protection (in production, use Redis or similar)
        self.pending_states: dict[str, datetime] = {}

    def generate_authorize_url(self) -> tuple[str, str]:
        """
        Generate OAuth2 authorization URL with state parameter.

        Returns:
            Tuple of (authorize_url, state)
        """
        state = secrets.token_urlsafe(32)
        self.pending_states[state] = datetime.now(timezone.utc)

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": self.provider.scope,
            "state": state,
        }

        authorize_url = f"{self.provider.authorize_url}?{urlencode(params)}"
        return authorize_url, state

    def verify_state(self, state: str) -> bool:
        """
        Verify OAuth2 state parameter for CSRF protection.

        Args:
            state: State parameter to verify

        Returns:
            True if state is valid, False otherwise
        """
        if state not in self.pending_states:
            return False

        # Check if state is not expired (valid for 10 minutes)
        created_at = self.pending_states[state]
        if datetime.now(timezone.utc) - created_at > timedelta(minutes=10):
            del self.pending_states[state]
            return False

        # Remove state after verification (one-time use)
        del self.pending_states[state]
        return True

    async def exchange_code_for_token(self, code: str) -> str | None:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from OAuth2 provider

        Returns:
            Access token if successful, None otherwise
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.provider.token_url,
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": self.redirect_uri,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code != 200:  # noqa: PLR2004
                    return None

                token_data = response.json()
                return token_data.get("access_token")

        except Exception:
            return None

    async def authenticate_with_oauth2(self, oauth_credentials: OAuth2Credentials) -> AuthenticationResponse:
        """
        Authenticate user with OAuth2 access token.

        Args:
            oauth_credentials: OAuth2 credentials with access token

        Returns:
            AuthenticationResponse with user and JWT token
        """
        try:
            # Fetch user info from provider
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.provider.user_info_url,
                    headers={"Authorization": f"{oauth_credentials.token_type} {oauth_credentials.access_token}"},
                )

                if response.status_code != 200:  # noqa: PLR2004
                    return AuthenticationResponse(
                        success=False,
                        error_message=f"Failed to fetch user info from {self.provider.name}: {response.status_code}",
                    )

                user_data = response.json()

            # Create User object from provider data
            user = self.provider.create_user_from_data(user_data)

            # Create JWT token
            jwt_token = self._create_jwt_token(user)

            return AuthenticationResponse(success=True, user=user, jwt_token=jwt_token)

        except Exception as e:
            return AuthenticationResponse(
                success=False,
                error_message=f"OAuth2 authentication failed: {str(e)}",
            )

    def _create_jwt_token(self, user: User) -> JWTToken:
        """Create a JWT token for the user."""
        now = datetime.now(timezone.utc)
        expires_in = self.token_expiry_minutes * 60

        payload = {
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "roles": user.roles,
            "metadata": user.metadata,
            "iat": now,
            "exp": now + timedelta(minutes=self.token_expiry_minutes),
        }

        access_token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

        return JWTToken(
            access_token=access_token,
            token_type="bearer",  # noqa: S106
            expires_in=expires_in,
            user=user,
        )

    async def authenticate_with_credentials(self, credentials: UserCredentials) -> AuthenticationResponse:  # noqa: PLR6301
        """
        OAuth2 backend does not support credential authentication.

        Args:
            credentials: User credentials

        Returns:
            AuthenticationResponse with error
        """
        return AuthenticationResponse(
            success=False,
            error_message="Credential authentication not supported by OAuth2 backend",
        )

    async def validate_token(self, token: str) -> AuthenticationResponse:
        """Validate a JWT token."""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])

            user = User(
                user_id=payload["user_id"],
                username=payload["username"],
                email=payload.get("email"),
                full_name=payload.get("full_name"),
                roles=payload.get("roles", []),
                metadata=payload.get("metadata", {}),
            )

            return AuthenticationResponse(success=True, user=user)

        except ExpiredSignatureError:
            return AuthenticationResponse(success=False, error_message="Token expired")
        except JWTError:
            return AuthenticationResponse(success=False, error_message="Invalid token")

    async def revoke_token(self, token: str) -> bool:
        """
        Revoke a JWT token.

        Args:
            token: The JWT token to revoke

        Raises:
            NotImplementedError: This method is not implemented
        """
        raise NotImplementedError(
            "OAuth2AuthenticationBackend does not support token revocation. "
            "Consider implementing your own backend with token revocation support."
        )


class MultiAuthenticationBackend(AuthenticationBackend):
    """
    Authentication backend that supports multiple authentication methods.

    This backend allows combining credentials-based and OAuth2 authentication,
    enabling users to choose their preferred login method.
    """

    def __init__(
        self,
        backends: list[AuthenticationBackend],
        default_options: AuthOptions | None = None,
    ):
        """
        Initialize multi-authentication backend.

        Args:
            backends: List of authentication backends to support
            default_options: Default options for the component
        """
        if not backends:
            raise ValueError("At least one authentication backend must be provided")

        if default_options is None:
            default_options = AuthOptions()
        super().__init__(default_options)

        self.backends = backends

        # Use the first backend's JWT configuration
        first_backend = backends[0]
        if hasattr(first_backend, "jwt_secret"):
            self.jwt_secret = first_backend.jwt_secret
            self.jwt_algorithm = getattr(first_backend, "jwt_algorithm", default_options.jwt_algorithm)
            self.token_expiry_minutes = getattr(
                first_backend, "token_expiry_minutes", default_options.token_expiry_minutes
            )
        else:
            # Fallback if first backend doesn't have JWT config
            self.jwt_secret = get_secret_key()
            self.jwt_algorithm = default_options.jwt_algorithm
            self.token_expiry_minutes = default_options.token_expiry_minutes

    def get_oauth2_backends(self) -> list[OAuth2AuthenticationBackend]:
        """Get all OAuth2 backends."""
        return [b for b in self.backends if isinstance(b, OAuth2AuthenticationBackend)]

    def get_credentials_backends(self) -> list[AuthenticationBackend]:
        """Get all credentials-based backends."""
        return [b for b in self.backends if not isinstance(b, OAuth2AuthenticationBackend)]

    async def authenticate_with_credentials(self, credentials: UserCredentials) -> AuthenticationResponse:
        """
        Try to authenticate with credentials using all credentials-based backends.

        Args:
            credentials: User credentials

        Returns:
            AuthenticationResponse from the first successful backend
        """
        errors = []

        for backend in self.get_credentials_backends():
            result = await backend.authenticate_with_credentials(credentials)
            if result.success:
                return result
            if result.error_message:
                errors.append(result.error_message)

        # All backends failed
        error_msg = "; ".join(errors) if errors else "Authentication failed"
        return AuthenticationResponse(success=False, error_message=error_msg)

    async def authenticate_with_oauth2(self, oauth_credentials: OAuth2Credentials) -> AuthenticationResponse:
        """
        Try to authenticate with OAuth2 using all OAuth2 backends.

        Args:
            oauth_credentials: OAuth2 credentials

        Returns:
            AuthenticationResponse from the first successful backend
        """
        errors = []

        for backend in self.get_oauth2_backends():
            result = await backend.authenticate_with_oauth2(oauth_credentials)
            if result.success:
                return result
            if result.error_message:
                errors.append(result.error_message)

        # All backends failed
        error_msg = "; ".join(errors) if errors else "OAuth2 authentication failed"
        return AuthenticationResponse(success=False, error_message=error_msg)

    async def validate_token(self, token: str) -> AuthenticationResponse:
        """
        Validate JWT token using all backends.

        Args:
            token: JWT token to validate

        Returns:
            AuthenticationResponse if any backend successfully validates
        """
        for backend in self.backends:
            result = await backend.validate_token(token)
            if result.success:
                return result

        return AuthenticationResponse(success=False, error_message="Invalid token")

    async def revoke_token(self, token: str) -> bool:
        """
        Revoke a JWT token.

        Args:
            token: The JWT token to revoke

        Raises:
            NotImplementedError: This method is not implemented
        """
        raise NotImplementedError(
            "MultiAuthenticationBackend does not support token revocation. "
            "Consider implementing your own backend with token revocation support."
        )
