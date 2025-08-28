import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, cast

import bcrypt
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
