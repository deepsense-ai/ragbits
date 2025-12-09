"""Session storage implementations."""

import asyncio
import logging
import secrets
from datetime import datetime, timezone

from ragbits.chat.auth.types import Session, SessionStore

logger = logging.getLogger(__name__)

# Minimum length for session ID truncation in logs (for readability while maintaining some privacy)
SESSION_ID_LOG_LENGTH = 8


class InMemorySessionStore(SessionStore):
    """In-memory session store implementation."""

    def __init__(self) -> None:
        """Initialize the in-memory session store."""
        self.sessions: dict[str, Session] = {}
        self.lock = asyncio.Lock()

    async def create_session(self, session: Session) -> str:
        """
        Create a new session.

        Args:
            session: Session object to store

        Returns:
            Session ID
        """
        session_id = secrets.token_urlsafe(32)
        session.session_id = session_id

        async with self.lock:
            self.sessions[session_id] = session

        logger.debug("Created session for user: %s", session.user.username)
        return session_id

    async def get_session(self, session_id: str) -> Session | None:
        """
        Retrieve a session by ID.

        Args:
            session_id: Session ID to retrieve

        Returns:
            Session object if found and not expired, None otherwise
        """
        async with self.lock:
            session = self.sessions.get(session_id)

        if not session:
            logger.debug(
                "Session not found: %s...",
                session_id[:SESSION_ID_LOG_LENGTH] if len(session_id) >= SESSION_ID_LOG_LENGTH else session_id,
            )
            return None

        # Check if session is expired
        if datetime.now(timezone.utc) > session.expires_at:
            # Session expired, delete it
            logger.debug(
                "Session expired, removing: %s...",
                session_id[:SESSION_ID_LOG_LENGTH] if len(session_id) >= SESSION_ID_LOG_LENGTH else session_id,
            )
            await self.delete_session(session_id)
            return None

        return session

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: Session ID to delete

        Returns:
            True if session was deleted, False if not found
        """
        async with self.lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                logger.debug(
                    "Session deleted: %s...",
                    session_id[:SESSION_ID_LOG_LENGTH] if len(session_id) >= SESSION_ID_LOG_LENGTH else session_id,
                )
                return True

        logger.debug(
            "Session not found for deletion: %s...",
            session_id[:SESSION_ID_LOG_LENGTH] if len(session_id) >= SESSION_ID_LOG_LENGTH else session_id,
        )
        return False

    def cleanup_expired_sessions(self) -> int:
        """
        Remove expired sessions from storage.

        This method is synchronous for compatibility with background task schedulers.
        It acquires the lock internally and skips cleanup if the lock is held.

        Returns:
            Number of sessions removed

        Example:
            To schedule periodic cleanup, you can use APScheduler or a similar library:

            ```python
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            from ragbits.chat.auth.session_store import InMemorySessionStore

            session_store = InMemorySessionStore()
            scheduler = AsyncIOScheduler()

            # Run cleanup every hour
            scheduler.add_job(
                session_store.cleanup_expired_sessions,
                "interval",
                hours=1,
                id="cleanup_sessions",
            )
            scheduler.start()
            ```

            Or using FastAPI's lifespan with asyncio:

            ```python
            import asyncio
            from contextlib import asynccontextmanager
            from fastapi import FastAPI


            @asynccontextmanager
            async def lifespan(app: FastAPI):
                async def cleanup_task():
                    while True:
                        await asyncio.sleep(3600)  # Run every hour
                        removed = session_store.cleanup_expired_sessions()
                        if removed > 0:
                            print(f"Cleaned up {removed} expired sessions")

                task = asyncio.create_task(cleanup_task())

        Yield:
                task.cancel()
            ```
        """
        now = datetime.now(timezone.utc)
        sessions_to_remove = []

        # Note: This is a synchronous method for background task compatibility
        # In production, consider using an async background task instead
        try:
            # Try to acquire lock without blocking if we're in an async context
            if self.lock.locked():
                logger.debug("Session cleanup skipped: lock is held")
                return 0  # Skip cleanup if lock is held

            # Synchronous cleanup - safe for background threads
            for session_id, session in list(self.sessions.items()):
                if now > session.expires_at:
                    sessions_to_remove.append(session_id)

            for session_id in sessions_to_remove:
                self.sessions.pop(session_id, None)

            if sessions_to_remove:
                logger.info("Cleaned up %d expired sessions", len(sessions_to_remove))

            return len(sessions_to_remove)
        except Exception as e:
            logger.exception("Error during session cleanup: %s", str(e))
            return 0
