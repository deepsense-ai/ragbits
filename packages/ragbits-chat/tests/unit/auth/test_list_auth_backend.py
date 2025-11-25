from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from ragbits.chat.auth.backends import ListAuthenticationBackend
from ragbits.chat.auth.session_store import InMemorySessionStore
from ragbits.chat.auth.types import OAuth2Credentials, Session, User, UserCredentials


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
def session_store():
    """Create a session store for testing."""
    return InMemorySessionStore()


@pytest.fixture
def auth_backend(test_users: list[dict[str, Any]], session_store: InMemorySessionStore) -> ListAuthenticationBackend:
    """Create a ListAuthBackend instance for testing."""
    return ListAuthenticationBackend(
        users=test_users,
        session_store=session_store,
        session_expiry_hours=24,
    )


class TestListAuthInitialization:
    """Test ListAuthBackend initialization."""

    @staticmethod
    def test_init_with_users_and_session_store(
        test_users: list[dict[str, Any]], session_store: InMemorySessionStore
    ) -> None:
        """Test that users and session store are properly initialized."""
        backend = ListAuthenticationBackend(
            users=test_users,
            session_store=session_store,
            session_expiry_hours=24,
        )

        assert len(backend.users) == 3
        assert "alice" in backend.users
        assert "bob" in backend.users
        assert "charlie" in backend.users
        assert backend.session_store is not None
        assert backend.session_expiry_hours == 24

        # Verify password hashing
        assert "password_hash" in backend.users["alice"]
        test_password = "password123"  # noqa: S105
        assert backend.users["alice"]["password_hash"] != test_password

        # Verify user objects
        from typing import cast

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
    def test_custom_session_expiry(test_users: list[dict[str, Any]], session_store: InMemorySessionStore) -> None:
        """Test initialization with custom session expiry."""
        backend = ListAuthenticationBackend(
            users=test_users,
            session_store=session_store,
            session_expiry_hours=48,
        )

        assert backend.session_expiry_hours == 48


class TestListAuthCredentialAuthentication:
    """Test credential-based authentication."""

    @pytest.mark.asyncio
    @staticmethod
    async def test_authenticate_valid_credentials(auth_backend: ListAuthenticationBackend) -> None:
        """Test authentication with valid credentials."""
        test_password = "password123"  # noqa: S106,S105
        credentials = UserCredentials(username="alice", password=test_password)
        result = await auth_backend.authenticate_with_credentials(credentials)

        assert result.success is True
        assert result.error_message is None
        assert result.user is not None
        assert result.session_id is not None

        # Verify user data
        assert result.user.username == "alice"
        assert result.user.email == "alice@example.com"
        assert result.user.full_name == "Alice Smith"
        assert result.user.roles == ["admin", "user"]

        # Verify session was created in store
        session = await auth_backend.session_store.get_session(result.session_id)
        assert session is not None
        assert session.user.username == "alice"
        assert session.provider == "credentials"

    @pytest.mark.asyncio
    @staticmethod
    async def test_authenticate_invalid_username(auth_backend: ListAuthenticationBackend) -> None:
        """Test authentication with non-existent username."""
        test_password = "password123"  # noqa: S106,S105
        credentials = UserCredentials(username="nonexistent", password=test_password)
        result = await auth_backend.authenticate_with_credentials(credentials)

        assert result.success is False
        assert result.error_message == "User not found"
        assert result.user is None
        assert result.session_id is None

    @pytest.mark.asyncio
    @staticmethod
    async def test_authenticate_invalid_password(auth_backend: ListAuthenticationBackend) -> None:
        """Test authentication with wrong password."""
        wrong_password = "wrongpassword"  # noqa: S106,S105
        credentials = UserCredentials(username="alice", password=wrong_password)
        result = await auth_backend.authenticate_with_credentials(credentials)

        assert result.success is False
        assert result.error_message == "Invalid password"
        assert result.user is None
        assert result.session_id is None

    @pytest.mark.asyncio
    @staticmethod
    async def test_authenticate_minimal_user_data(auth_backend: ListAuthenticationBackend) -> None:
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
        assert result.session_id is not None


class TestListAuthSessionOperations:
    """Test session creation and validation."""

    @pytest.mark.asyncio
    @staticmethod
    async def test_validate_valid_session(auth_backend: ListAuthenticationBackend) -> None:
        """Test validation of valid session."""
        # Create a session by authenticating
        test_password = "password123"  # noqa: S106,S105
        credentials = UserCredentials(username="alice", password=test_password)
        auth_result = await auth_backend.authenticate_with_credentials(credentials)

        # Validate the session
        assert auth_result.session_id is not None
        result = await auth_backend.validate_session(auth_result.session_id)

        assert result.success is True
        assert result.error_message is None
        assert result.user is not None
        assert result.user.username == "alice"
        assert result.user.email == "alice@example.com"

    @pytest.mark.asyncio
    @staticmethod
    async def test_validate_invalid_session(auth_backend: ListAuthenticationBackend) -> None:
        """Test validation of invalid session ID."""
        result = await auth_backend.validate_session("invalid-session-id")

        assert result.success is False
        assert result.error_message == "Invalid or expired session"
        assert result.user is None

    @pytest.mark.asyncio
    @staticmethod
    async def test_validate_expired_session(
        auth_backend: ListAuthenticationBackend, session_store: InMemorySessionStore
    ) -> None:
        """Test validation of expired session."""
        # Create an expired session directly
        user = User(user_id="test", username="test")
        now = datetime.now(timezone.utc)
        expired_session = Session(
            session_id="expired-session",
            user=user,
            provider="credentials",
            oauth_token="",
            token_type="",
            created_at=now - timedelta(hours=48),
            expires_at=now - timedelta(hours=24),  # Expired
        )

        # Manually add to session store
        session_store.sessions["expired-session"] = expired_session

        # Try to validate - should fail and be removed
        result = await auth_backend.validate_session("expired-session")

        assert result.success is False
        assert result.error_message == "Invalid or expired session"
        assert result.user is None

        # Session should be removed from store
        assert "expired-session" not in session_store.sessions


class TestListAuthSessionRevocation:
    """Test session revocation functionality."""

    @pytest.mark.asyncio
    @staticmethod
    async def test_revoke_valid_session(auth_backend: ListAuthenticationBackend) -> None:
        """Test revoking a valid session."""
        # Create session
        test_password = "password123"  # noqa: S106,S105
        credentials = UserCredentials(username="alice", password=test_password)
        auth_result = await auth_backend.authenticate_with_credentials(credentials)
        assert auth_result.session_id is not None
        session_id = auth_result.session_id

        # Session should be valid
        result = await auth_backend.validate_session(session_id)
        assert result.success is True

        # Revoke the session
        success = await auth_backend.revoke_session(session_id)
        assert success is True

        # Session should no longer be valid
        result = await auth_backend.validate_session(session_id)
        assert result.success is False

    @pytest.mark.asyncio
    @staticmethod
    async def test_revoke_invalid_session(auth_backend: ListAuthenticationBackend) -> None:
        """Test revoking an invalid session ID."""
        success = await auth_backend.revoke_session("invalid-session-id")
        assert success is False

    @pytest.mark.asyncio
    @staticmethod
    async def test_revoke_multiple_sessions(auth_backend: ListAuthenticationBackend) -> None:
        """Test revoking multiple sessions."""
        # Create two sessions
        alice_password = "password123"  # noqa: S106,S105
        bob_password = "secret456"  # noqa: S106,S105
        alice_creds = UserCredentials(username="alice", password=alice_password)
        bob_creds = UserCredentials(username="bob", password=bob_password)

        alice_result = await auth_backend.authenticate_with_credentials(alice_creds)
        bob_result = await auth_backend.authenticate_with_credentials(bob_creds)

        # Both sessions should be valid
        assert alice_result.session_id is not None
        assert bob_result.session_id is not None
        alice_validation = await auth_backend.validate_session(alice_result.session_id)
        bob_validation = await auth_backend.validate_session(bob_result.session_id)
        assert alice_validation.success is True
        assert bob_validation.success is True

        # Revoke alice's session
        success = await auth_backend.revoke_session(alice_result.session_id)
        assert success is True

        # Alice's session should be invalid, Bob's should still be valid
        alice_validation = await auth_backend.validate_session(alice_result.session_id)
        bob_validation = await auth_backend.validate_session(bob_result.session_id)
        assert alice_validation.success is False
        assert bob_validation.success is True


class TestListAuthOAuth2:
    """Test OAuth2 authentication (should not be supported)."""

    @pytest.mark.asyncio
    @staticmethod
    async def test_oauth2_not_supported(auth_backend: ListAuthenticationBackend) -> None:
        """Test that OAuth2 authentication is not supported."""
        fake_token = "fake-token"  # noqa: S106,S105
        oauth_creds = OAuth2Credentials(access_token=fake_token)
        result = await auth_backend.authenticate_with_oauth2(oauth_creds)

        assert result.success is False
        assert result.error_message == "OAuth2 not supported by ListAuthentication"
        assert result.user is None
        assert result.session_id is None


class TestListAuthPasswordSecurity:
    """Test password security features."""

    @staticmethod
    def test_password_hashing_with_bcrypt(
        test_users: list[dict[str, Any]], session_store: InMemorySessionStore
    ) -> None:
        """Test that passwords are properly hashed with bcrypt."""
        backend = ListAuthenticationBackend(
            users=test_users,
            session_store=session_store,
        )

        # Verify passwords are hashed
        for username in ["alice", "bob", "charlie"]:
            password_hash = backend.users[username]["password_hash"]
            # Plain text passwords from test data
            assert password_hash not in ["password123", "secret456", "test789"]
            assert isinstance(password_hash, str)
            assert password_hash.startswith("$2b$")  # bcrypt format

    @staticmethod
    def test_different_users_different_salts(session_store: InMemorySessionStore) -> None:
        """Test that different users get different password hashes even with same password."""
        # Create users with same password
        same_password_users = [
            {"username": "user1", "password": "samepassword"},  # noqa: S106
            {"username": "user2", "password": "samepassword"},  # noqa: S106
        ]

        backend = ListAuthenticationBackend(
            users=same_password_users,
            session_store=session_store,
        )

        hash1 = backend.users["user1"]["password_hash"]
        hash2 = backend.users["user2"]["password_hash"]

        # Hashes should be different due to different salts
        assert hash1 != hash2


class TestListAuthIntegration:
    """Integration tests for complete authentication flow."""

    @pytest.mark.asyncio
    @staticmethod
    async def test_complete_session_flow(auth_backend: ListAuthenticationBackend) -> None:
        """Test complete flow: authenticate -> validate -> revoke."""
        # Step 1: Authenticate
        test_password = "password123"  # noqa: S106,S105
        credentials = UserCredentials(username="alice", password=test_password)
        auth_result = await auth_backend.authenticate_with_credentials(credentials)

        assert auth_result.success is True
        assert auth_result.session_id is not None

        # Step 2: Validate session
        session_id = auth_result.session_id
        validate_result = await auth_backend.validate_session(session_id)

        assert validate_result.success is True
        assert validate_result.user is not None
        assert validate_result.user.username == "alice"

        # Step 3: Revoke session
        revoke_success = await auth_backend.revoke_session(session_id)
        assert revoke_success is True

        # Step 4: Verify session is invalid after revocation
        validate_after_revoke = await auth_backend.validate_session(session_id)
        assert validate_after_revoke.success is False

    @pytest.mark.asyncio
    @staticmethod
    async def test_multiple_user_sessions(auth_backend: ListAuthenticationBackend) -> None:
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

        # Both sessions should be valid
        assert alice_result.session_id is not None
        assert bob_result.session_id is not None
        alice_validation = await auth_backend.validate_session(alice_result.session_id)
        bob_validation = await auth_backend.validate_session(bob_result.session_id)

        assert alice_validation.success is True
        assert bob_validation.success is True
        assert alice_validation.user is not None
        assert alice_validation.user.username == "alice"
        assert bob_validation.user is not None
        assert bob_validation.user.username == "bob"

    @pytest.mark.asyncio
    @staticmethod
    async def test_session_expiry_configuration(
        test_users: list[dict[str, Any]], session_store: InMemorySessionStore
    ) -> None:
        """Test that session expiry is properly configured."""
        backend = ListAuthenticationBackend(
            users=test_users,
            session_store=session_store,
            session_expiry_hours=12,
        )

        test_password = "password123"  # noqa: S106,S105
        credentials = UserCredentials(username="alice", password=test_password)
        result = await backend.authenticate_with_credentials(credentials)

        # Get the session from store
        assert result.session_id is not None
        session = await session_store.get_session(result.session_id)
        assert session is not None

        # Check expiry time is approximately 12 hours from now
        time_diff = session.expires_at - session.created_at
        assert time_diff.total_seconds() == pytest.approx(12 * 3600, abs=1)
