from datetime import datetime, timezone
from typing import Any, cast

import pytest
from jose import jwt

from ragbits.chat.auth.backends import ListAuthentication
from ragbits.chat.auth.base import AuthOptions
from ragbits.chat.auth.types import OAuth2Credentials, User, UserCredentials


@pytest.fixture
def test_users():
    """Sample user data for testing."""
    return [
        {
            "user_id": "user1",
            "username": "alice",
            "password": "password123",
            "email": "alice@example.com",
            "full_name": "Alice Smith",
            "roles": ["admin", "user"],
            "metadata": {"department": "engineering"},
        },
        {
            "username": "bob",
            "password": "secret456",
            "email": "bob@example.com",
            "full_name": "Bob Johnson",
            "roles": ["user"],
        },
        {
            "username": "charlie",
            "password": "test789",
        },
    ]


@pytest.fixture
def auth_backend(test_users: list[dict[str, Any]]) -> ListAuthentication:
    """Create a ListAuthBackend instance for testing."""
    jwt_secret = "test-secret-key"  # noqa: S106,S105
    return ListAuthentication(users=test_users, default_options=AuthOptions(), jwt_secret=jwt_secret)


class TestListAuthInitialization:
    """Test ListAuthBackend initialization."""

    @staticmethod
    def test_init_with_users(test_users: list[dict[str, Any]]) -> None:
        """Test that users are properly initialized."""
        backend = ListAuthentication(users=test_users, default_options=AuthOptions())

        assert len(backend.users) == 3
        assert "alice" in backend.users
        assert "bob" in backend.users
        assert "charlie" in backend.users

        # Verify password hashing
        assert "password_hash" in backend.users["alice"]
        test_password = "password123"  # noqa: S105
        assert backend.users["alice"]["password_hash"] != test_password

        # Verify user objects
        alice_user: User = cast(User, backend.users["alice"]["user"])
        assert alice_user.user_id == "user1"
        assert alice_user.username == "alice"
        assert alice_user.email == "alice@example.com"
        assert alice_user.full_name == "Alice Smith"
        assert alice_user.roles == ["admin", "user"]
        assert alice_user.metadata == {"department": "engineering"}

        # Verify user with minimal data
        charlie_user: User = cast(User, backend.users["charlie"]["user"])
        assert charlie_user.username == "charlie"
        assert charlie_user.email is None
        assert charlie_user.full_name is None
        assert charlie_user.roles == []
        assert charlie_user.metadata == {}

    @staticmethod
    def test_init_with_custom_jwt_secret(test_users: list[dict[str, Any]]) -> None:
        """Test initialization with custom JWT secret."""
        custom_secret = "my-custom-secret"  # noqa: S105
        backend = ListAuthentication(users=test_users, default_options=AuthOptions(), jwt_secret=custom_secret)

        assert backend.jwt_secret == custom_secret

    @staticmethod
    def test_init_without_jwt_secret(test_users: list[dict[str, Any]]) -> None:
        """Test initialization without JWT secret generates random one."""
        backend = ListAuthentication(users=test_users, default_options=AuthOptions())

        assert backend.jwt_secret is not None
        assert len(backend.jwt_secret) > 0

    @staticmethod
    def test_default_configuration(test_users: list[dict[str, Any]]) -> None:
        """Test default configuration values."""
        backend = ListAuthentication(users=test_users, default_options=AuthOptions())

        assert backend.jwt_algorithm == "HS256"
        assert backend.token_expiry_minutes == 30
        assert isinstance(backend.revoked_tokens, set)
        assert len(backend.revoked_tokens) == 0


class TestListAuthCredentialAuthentication:
    """Test credential-based authentication."""

    @pytest.mark.asyncio
    @staticmethod
    async def test_authenticate_valid_credentials(auth_backend: ListAuthentication) -> None:
        """Test authentication with valid credentials."""
        test_password = "password123"  # noqa: S106,S105
        credentials = UserCredentials(username="alice", password=test_password)
        result = await auth_backend.authenticate_with_credentials(credentials)

        assert result.success is True
        assert result.error_message is None
        assert result.user is not None
        assert result.jwt_token is not None

        # Verify user data
        assert result.user.username == "alice"
        assert result.user.email == "alice@example.com"
        assert result.user.full_name == "Alice Smith"
        assert result.user.roles == ["admin", "user"]

        # Verify JWT token
        assert result.jwt_token.access_token is not None
        bearer_type = "bearer"  # noqa: S105
        assert result.jwt_token.token_type == bearer_type
        assert result.jwt_token.expires_in == 30 * 60  # 30 minutes in seconds
        assert result.jwt_token.user == result.user

    @pytest.mark.asyncio
    @staticmethod
    async def test_authenticate_invalid_username(auth_backend: ListAuthentication) -> None:
        """Test authentication with non-existent username."""
        test_password = "password123"  # noqa: S106,S105
        credentials = UserCredentials(username="nonexistent", password=test_password)
        result = await auth_backend.authenticate_with_credentials(credentials)

        assert result.success is False
        assert result.error_message == "User not found"
        assert result.user is None
        assert result.jwt_token is None

    @pytest.mark.asyncio
    @staticmethod
    async def test_authenticate_invalid_password(auth_backend: ListAuthentication) -> None:
        """Test authentication with wrong password."""
        wrong_password = "wrongpassword"  # noqa: S106,S105
        credentials = UserCredentials(username="alice", password=wrong_password)
        result = await auth_backend.authenticate_with_credentials(credentials)

        assert result.success is False
        assert result.error_message == "Invalid password"
        assert result.user is None
        assert result.jwt_token is None

    @pytest.mark.asyncio
    @staticmethod
    async def test_authenticate_minimal_user_data(auth_backend: ListAuthentication) -> None:
        """Test authentication with user having minimal data."""
        test_password = "test789"  # noqa: S106,S105
        credentials = UserCredentials(username="charlie", password=test_password)
        result = await auth_backend.authenticate_with_credentials(credentials)

        assert result.success is True
        assert result.user is not None
        assert result.user.username == "charlie"
        assert result.user.email is None
        assert result.user.full_name is None
        assert result.user.roles == []
        assert result.user.metadata == {}


class TestListAuthJWTTokenOperations:
    """Test JWT token creation and validation."""

    @staticmethod
    def test_create_jwt_token(auth_backend: ListAuthentication) -> None:
        """Test JWT token creation."""
        user = User(
            user_id="test-user",
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            roles=["user"],
            metadata={"test": "data"},
        )

        jwt_token = auth_backend._create_jwt_token(user)

        assert jwt_token.access_token is not None
        bearer_type = "bearer"  # noqa: S105
        assert jwt_token.token_type == bearer_type
        assert jwt_token.expires_in == 30 * 60
        assert jwt_token.user == user

        # Verify token payload
        payload = jwt.decode(jwt_token.access_token, auth_backend.jwt_secret, algorithms=[auth_backend.jwt_algorithm])
        assert payload["user_id"] == user.user_id
        assert payload["username"] == user.username
        assert payload["email"] == user.email
        assert payload["full_name"] == user.full_name
        assert payload["roles"] == user.roles
        assert payload["metadata"] == user.metadata
        assert "iat" in payload
        assert "exp" in payload

    @pytest.mark.asyncio
    @staticmethod
    async def test_validate_valid_token(auth_backend: ListAuthentication) -> None:
        """Test validation of valid JWT token."""
        user = User(
            user_id="test-user",
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            roles=["user"],
            metadata={"test": "data"},
        )

        jwt_token = auth_backend._create_jwt_token(user)
        result = await auth_backend.validate_token(jwt_token.access_token)

        assert result.success is True
        assert result.error_message is None
        assert result.user is not None
        assert result.user.user_id == user.user_id
        assert result.user.username == user.username
        assert result.user.email == user.email
        assert result.user.full_name == user.full_name
        assert result.user.roles == user.roles
        assert result.user.metadata == user.metadata

    @pytest.mark.asyncio
    @staticmethod
    async def test_validate_invalid_token(auth_backend: ListAuthentication) -> None:
        """Test validation of invalid JWT token."""
        invalid_token = "invalid.jwt.token"  # noqa: S105
        result = await auth_backend.validate_token(invalid_token)

        assert result.success is False
        assert result.error_message == "Invalid jwt_token"
        assert result.user is None

    @pytest.mark.asyncio
    @staticmethod
    async def test_validate_expired_token(auth_backend: ListAuthentication) -> None:
        """Test validation of expired JWT token."""
        # Create token with negative expiry time
        user = User(user_id="test", username="test")
        payload = {
            "user_id": user.user_id,
            "username": user.username,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc).timestamp() - 3600,  # Expired 1 hour ago
        }

        expired_token = jwt.encode(payload, auth_backend.jwt_secret, algorithm=auth_backend.jwt_algorithm)
        result = await auth_backend.validate_token(expired_token)

        assert result.success is False
        assert result.error_message == "Token expired"
        assert result.user is None

    @pytest.mark.asyncio
    @staticmethod
    async def test_validate_token_with_wrong_secret(auth_backend: ListAuthentication) -> None:
        """Test validation of token signed with different secret."""
        user = User(user_id="test", username="test")
        wrong_secret = "wrong-secret"  # noqa: S105

        payload = {
            "user_id": user.user_id,
            "username": user.username,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc).timestamp() + 3600,
        }

        wrong_token = jwt.encode(payload, wrong_secret, algorithm=auth_backend.jwt_algorithm)
        result = await auth_backend.validate_token(wrong_token)

        assert result.success is False
        assert result.error_message == "Invalid jwt_token"
        assert result.user is None


class TestListAuthTokenRevocation:
    """Test token revocation functionality."""

    @pytest.mark.asyncio
    @staticmethod
    async def test_revoke_valid_token(auth_backend: ListAuthentication) -> None:
        """Test revoking a valid JWT token."""
        user = User(user_id="test", username="test")
        jwt_token = auth_backend._create_jwt_token(user)

        # Token should be valid initially
        result = await auth_backend.validate_token(jwt_token.access_token)
        assert result.success is True

        # Revoke the token
        revoke_result = await auth_backend.revoke_token(jwt_token.access_token)
        assert revoke_result is True

        # Token should be invalid after revocation
        result = await auth_backend.validate_token(jwt_token.access_token)
        assert result.success is False
        assert result.error_message == "Token has been revoked"

    @pytest.mark.asyncio
    @staticmethod
    async def test_revoke_invalid_token(auth_backend: ListAuthentication) -> None:
        """Test revoking an invalid JWT token."""
        invalid_token = "invalid.jwt.token"  # noqa: S105
        revoke_result = await auth_backend.revoke_token(invalid_token)

        assert revoke_result is False

    @pytest.mark.asyncio
    @staticmethod
    async def test_revoke_multiple_tokens(auth_backend: ListAuthentication) -> None:
        """Test revoking multiple tokens."""
        user1 = User(user_id="user1", username="user1")
        user2 = User(user_id="user2", username="user2")

        token1 = auth_backend._create_jwt_token(user1)
        token2 = auth_backend._create_jwt_token(user2)

        # Revoke both tokens
        result1 = await auth_backend.revoke_token(token1.access_token)
        result2 = await auth_backend.revoke_token(token2.access_token)

        assert result1 is True
        assert result2 is True
        assert len(auth_backend.revoked_tokens) == 2

        # Both tokens should be invalid
        validation1 = await auth_backend.validate_token(token1.access_token)
        validation2 = await auth_backend.validate_token(token2.access_token)

        assert validation1.success is False
        assert validation2.success is False


class TestListAuthTokenCleanup:
    """Test token cleanup functionality."""

    @staticmethod
    def test_cleanup_expired_tokens(auth_backend: ListAuthentication) -> None:
        """Test cleanup of expired tokens from revocation list."""
        # Add some expired tokens to the revoked list
        expired_payload = {
            "user_id": "test",
            "username": "test",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc).timestamp() - 3600,  # Expired 1 hour ago
        }
        expired_token = jwt.encode(expired_payload, auth_backend.jwt_secret, algorithm=auth_backend.jwt_algorithm)

        # Add valid token
        valid_payload = {
            "user_id": "test2",
            "username": "test2",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc).timestamp() + 3600,  # Valid for 1 hour
        }
        valid_token = jwt.encode(valid_payload, auth_backend.jwt_secret, algorithm=auth_backend.jwt_algorithm)

        # Add invalid token
        invalid_token = "invalid.token.format"  # noqa: S105

        # Add all tokens to revoked list
        auth_backend.revoked_tokens.add(expired_token)
        auth_backend.revoked_tokens.add(valid_token)
        auth_backend.revoked_tokens.add(invalid_token)

        assert len(auth_backend.revoked_tokens) == 3

        # Cleanup expired tokens
        removed_count = auth_backend.cleanup_expired_tokens()

        # Should remove expired and invalid tokens, keep valid one
        assert removed_count == 2
        assert len(auth_backend.revoked_tokens) == 1
        assert valid_token in auth_backend.revoked_tokens

    @staticmethod
    def test_cleanup_no_expired_tokens(auth_backend: ListAuthentication) -> None:
        """Test cleanup when no tokens are expired."""
        # Add only valid tokens
        valid_payload = {
            "user_id": "test",
            "username": "test",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc).timestamp() + 3600,
        }
        valid_token = jwt.encode(valid_payload, auth_backend.jwt_secret, algorithm=auth_backend.jwt_algorithm)

        auth_backend.revoked_tokens.add(valid_token)

        removed_count = auth_backend.cleanup_expired_tokens()

        assert removed_count == 0
        assert len(auth_backend.revoked_tokens) == 1


class TestListAuthOAuth2:
    """Test OAuth2 authentication (should not be supported)."""

    @pytest.mark.asyncio
    @staticmethod
    async def test_oauth2_not_supported(auth_backend: ListAuthentication) -> None:
        """Test that OAuth2 authentication is not supported."""
        fake_token = "fake-token"  # noqa: S106,S105
        oauth_creds = OAuth2Credentials(access_token=fake_token)
        result = await auth_backend.authenticate_with_oauth2(oauth_creds)

        assert result.success is False
        assert result.error_message == "OAuth2 not supported by ListAuthentication"
        assert result.user is None
        assert result.jwt_token is None


class TestListAuthPasswordSecurity:
    """Test password security features."""

    @staticmethod
    def test_password_hashing_with_bcrypt(test_users: list[dict[str, Any]]) -> None:
        """Test that passwords are properly hashed with bcrypt."""
        backend = ListAuthentication(users=test_users, default_options=AuthOptions())

        # Verify passwords are hashed
        for username in ["alice", "bob", "charlie"]:
            password_hash = backend.users[username]["password_hash"]
            assert password_hash != test_users[0]["password"]  # Not plain text
            assert isinstance(password_hash, str)
            assert password_hash.startswith("$2b$")  # bcrypt format

    @staticmethod
    def test_different_users_different_salts(test_users: list[dict[str, Any]]) -> None:
        """Test that different users get different password hashes even with same password."""
        # Create users with same password
        same_password_users = [
            {"username": "user1", "password": "samepassword"},  # noqa: S106
            {"username": "user2", "password": "samepassword"},  # noqa: S106
        ]

        backend = ListAuthentication(users=same_password_users, default_options=AuthOptions())

        hash1 = backend.users["user1"]["password_hash"]
        hash2 = backend.users["user2"]["password_hash"]

        # Hashes should be different due to different salts
        assert hash1 != hash2


class TestListAuthIntegration:
    """Integration tests for complete authentication flow."""

    @pytest.mark.asyncio
    @staticmethod
    async def test_complete_authentication_flow(auth_backend: ListAuthentication) -> None:
        """Test complete flow: authenticate -> validate token -> revoke token."""
        # Step 1: Authenticate
        test_password = "password123"  # noqa: S106,S105
        credentials = UserCredentials(username="alice", password=test_password)
        auth_result = await auth_backend.authenticate_with_credentials(credentials)

        assert auth_result.success is True
        assert auth_result.jwt_token is not None

        # Step 2: Validate token
        token = auth_result.jwt_token.access_token
        validate_result = await auth_backend.validate_token(token)

        assert validate_result.success is True
        assert validate_result.user is not None
        assert validate_result.user.username == "alice"

        # Step 3: Revoke token
        revoke_result = await auth_backend.revoke_token(token)
        assert revoke_result is True

        # Step 4: Validate revoked token
        validate_revoked = await auth_backend.validate_token(token)
        assert validate_revoked.success is False
        assert validate_revoked.error_message == "Token has been revoked"

    @pytest.mark.asyncio
    @staticmethod
    async def test_multiple_user_sessions(auth_backend: ListAuthentication) -> None:
        """Test multiple users can authenticate simultaneously."""
        # Authenticate multiple users
        alice_password = "password123"  # noqa: S106,S105
        bob_password = "secret456"  # noqa: S106,S105
        alice_creds = UserCredentials(username="alice", password=alice_password)
        bob_creds = UserCredentials(username="bob", password=bob_password)

        alice_result = await auth_backend.authenticate_with_credentials(alice_creds)
        bob_result = await auth_backend.authenticate_with_credentials(bob_creds)

        assert alice_result.success is True
        assert bob_result.success is True

        # Both tokens should be valid
        assert alice_result.jwt_token is not None
        assert bob_result.jwt_token is not None
        alice_validation = await auth_backend.validate_token(alice_result.jwt_token.access_token)
        bob_validation = await auth_backend.validate_token(bob_result.jwt_token.access_token)

        assert alice_validation.success is True
        assert bob_validation.success is True
        assert alice_validation.user is not None
        assert alice_validation.user.username == "alice"
        assert bob_validation.user is not None
        assert bob_validation.user.username == "bob"
