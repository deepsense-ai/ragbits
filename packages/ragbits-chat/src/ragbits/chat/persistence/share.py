"""Persistence for conversation shares built on ``ragbits.core.storage``.

Stores share records (owner → recipient) for conversations using a pluggable
:class:`~ragbits.core.storage.connections.DatabaseConnection`. Postgres and
SQLite are supported out of the box; new dialects only have to declare a
``placeholder_style`` and (optionally) override the schema DDL via subclassing.

Recipient identifiers are normalised (lowercased, trimmed) before storage and
lookup so that sharing with a user by user_id, username, or email is symmetric
across casing.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Sequence
from typing import Any, ClassVar, TypeVar

from typing_extensions import Self

from ragbits.chat.persistence.base import SharePersistenceStrategy
from ragbits.core.options import Options
from ragbits.core.storage.connections import DatabaseConnection
from ragbits.core.utils.config_handling import ObjectConstructionConfig


def _normalize_identifier(identifier: str) -> str:
    """Canonicalise an identifier for case-insensitive comparisons."""
    return identifier.strip().lower()


def _coerce_identifiers(user_id: str | Sequence[str]) -> list[str]:
    """Normalize a single identifier or sequence into a deduplicated list.

    Empty strings are dropped and identifiers are lowercased so that owners,
    recipients, and access checks all compare against the same canonical form.
    """
    raw = [user_id] if isinstance(user_id, str) else list(user_id)
    seen: set[str] = set()
    result: list[str] = []
    for value in raw:
        if not value:
            continue
        normalized = _normalize_identifier(value)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


class SQLSharePersistenceOptions(Options):
    """Configuration options for :class:`SQLSharePersistence`."""

    shares_table: str = "ragbits_conversation_shares"


SQLSharePersistenceOptionsT = TypeVar("SQLSharePersistenceOptionsT", bound=SQLSharePersistenceOptions)


class SQLSharePersistence(SharePersistenceStrategy):
    """A SQL-backed share persistence using :class:`DatabaseConnection`.

    The connection determines the dialect (placeholder style and DDL flavour),
    so the same class works for PostgreSQL and SQLite. Multiple persistences
    may share the same underlying ``DatabaseConnection``; the class never
    closes the connection it was given — that lifecycle stays with the caller.

    Example:
        ```python
        from ragbits.core.storage.connections import SQLiteConnection
        from ragbits.chat.persistence.share import SQLSharePersistence

        connection = SQLiteConnection(":memory:")
        share = SQLSharePersistence(connection)
        async with connection:
            await share.set_shares("conv-1", "alice", ["bob"])
        ```
    """

    configuration_key: ClassVar = "share_persistence"

    def __init__(
        self,
        connection: DatabaseConnection[Any],
        options: SQLSharePersistenceOptions | None = None,
    ) -> None:
        """
        Args:
            connection: Database connection. Must be a known dialect
                (``placeholder_style`` of ``"qmark"`` or ``"numeric"``).
            options: Configuration for table names and other settings.

        Raises:
            TypeError: When ``connection`` is not a :class:`DatabaseConnection`
                or has an unsupported ``placeholder_style``.
        """
        if not isinstance(connection, DatabaseConnection):
            raise TypeError(f"connection must be a DatabaseConnection, got {type(connection).__name__}")
        if connection.placeholder_style not in ("qmark", "numeric"):
            raise TypeError(
                f"Unsupported placeholder_style: {connection.placeholder_style!r}. "
                "Expected 'qmark' (SQLite) or 'numeric' (Postgres)."
            )
        self._connection = connection
        self.options = options or SQLSharePersistenceOptions()
        self._schema_initialized = False
        self._init_lock = asyncio.Lock()

    @property
    def _table(self) -> str:
        return self.options.shares_table

    @property
    def _is_postgres(self) -> bool:
        return self._connection.placeholder_style == "numeric"

    def _ph(self, index: int) -> str:
        """Render a 1-based positional placeholder for the active dialect."""
        return self._connection.placeholder(index)

    def _placeholders(self, count: int, *, start: int = 1) -> str:
        """Render ``count`` comma-separated placeholders starting at ``start``."""
        return ", ".join(self._ph(start + i) for i in range(count))

    def _bool_literal(self, value: bool) -> str:
        """Render a SQL boolean literal (some SQLite versions lack TRUE/FALSE)."""
        if self._is_postgres:
            return "TRUE" if value else "FALSE"
        return "1" if value else "0"

    @staticmethod
    def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
        """Normalise a raw row so callers see consistent types across dialects."""
        result = dict(row)
        if "hidden" in result:
            result["hidden"] = bool(result["hidden"])
        return result

    async def _init_db(self) -> None:
        """Create tables on first use. Safe to call repeatedly and concurrently."""
        if self._schema_initialized:
            return
        async with self._init_lock:
            if self._schema_initialized:
                return
            await self._connection._ensure_connected()
            if self._is_postgres:
                ddl = f"""
                CREATE TABLE IF NOT EXISTS {self._table} (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    owner_id TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    shared_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    hidden BOOLEAN NOT NULL DEFAULT FALSE,
                    UNIQUE (conversation_id, recipient)
                )
                """  # noqa: S608
            else:
                ddl = f"""
                CREATE TABLE IF NOT EXISTS {self._table} (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    owner_id TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    shared_at REAL NOT NULL DEFAULT (strftime('%s','now')),
                    hidden INTEGER NOT NULL DEFAULT 0,
                    UNIQUE (conversation_id, recipient)
                )
                """  # noqa: S608
            await self._connection.execute(ddl)
            await self._connection.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{self._table}_conv "  # noqa: S608
                f"ON {self._table} (conversation_id)"
            )
            await self._connection.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{self._table}_recipient "  # noqa: S608
                f"ON {self._table} (recipient)"
            )
            self._schema_initialized = True

    async def set_shares(
        self,
        conversation_id: str,
        owner_id: str,
        recipients: list[str],
    ) -> list[dict[str, Any]]:
        """Create or refresh share rows for ``recipients`` under ``owner_id``.

        Uses an UPSERT so concurrent calls converge on the same final state
        without raising on the ``UNIQUE (conversation_id, recipient)``
        constraint. Each row insert/update is performed inside a single
        transaction so the call is atomic per request.
        """
        normalized_owner = _normalize_identifier(owner_id)
        normalized_recipients = _coerce_identifiers(recipients)
        if not normalized_recipients:
            return []

        await self._init_db()

        rows: list[dict[str, Any]] = []
        async with self._connection.transaction():
            for recipient in normalized_recipients:
                share_id = str(uuid.uuid4())
                if self._is_postgres:
                    sql = (
                        f"INSERT INTO {self._table} "  # noqa: S608
                        "(id, conversation_id, owner_id, recipient, shared_at, hidden) "
                        f"VALUES ({self._ph(1)}, {self._ph(2)}, {self._ph(3)}, {self._ph(4)}, NOW(), FALSE) "
                        "ON CONFLICT (conversation_id, recipient) DO UPDATE SET "
                        "owner_id = EXCLUDED.owner_id, shared_at = NOW(), hidden = FALSE "
                        "RETURNING id, conversation_id, owner_id, recipient, shared_at, hidden"
                    )
                    row = await self._connection.fetch_one(sql, share_id, conversation_id, normalized_owner, recipient)
                else:
                    now_ts = time.time()
                    sql = (
                        f"INSERT INTO {self._table} "  # noqa: S608
                        "(id, conversation_id, owner_id, recipient, shared_at, hidden) "
                        "VALUES (?, ?, ?, ?, ?, 0) "
                        "ON CONFLICT (conversation_id, recipient) DO UPDATE SET "
                        "owner_id = excluded.owner_id, shared_at = excluded.shared_at, hidden = 0"
                    )
                    await self._connection.execute(sql, share_id, conversation_id, normalized_owner, recipient, now_ts)
                    row = await self._connection.fetch_one(
                        f"SELECT id, conversation_id, owner_id, recipient, shared_at, hidden "  # noqa: S608
                        f"FROM {self._table} WHERE conversation_id = ? AND recipient = ?",
                        conversation_id,
                        recipient,
                    )
                if row is not None:
                    rows.append(self._normalize_row(row))
        return rows

    async def get_shares(self, conversation_id: str, owner_id: str) -> list[dict[str, Any]]:
        """Return the visible shares of ``conversation_id`` owned by ``owner_id``."""
        await self._init_db()
        normalized_owner = _normalize_identifier(owner_id)
        sql = (
            f"SELECT id, conversation_id, owner_id, recipient, shared_at, hidden "  # noqa: S608
            f"FROM {self._table} "
            f"WHERE conversation_id = {self._ph(1)} "
            f"AND owner_id = {self._ph(2)} "
            f"AND hidden = {self._bool_literal(False)} "
            f"ORDER BY shared_at DESC"
        )
        rows = await self._connection.fetch_all(sql, conversation_id, normalized_owner)
        return [self._normalize_row(r) for r in rows]

    async def remove_shares(
        self,
        conversation_id: str,
        owner_id: str,
        recipients: list[str],
    ) -> None:
        """Delete share rows that match ``conversation_id``, ``owner_id`` and any of ``recipients``."""
        normalized_recipients = _coerce_identifiers(recipients)
        if not normalized_recipients:
            return

        await self._init_db()
        normalized_owner = _normalize_identifier(owner_id)

        in_list = self._placeholders(len(normalized_recipients), start=3)
        sql = (
            f"DELETE FROM {self._table} "  # noqa: S608
            f"WHERE conversation_id = {self._ph(1)} "
            f"AND owner_id = {self._ph(2)} "
            f"AND recipient IN ({in_list})"
        )
        await self._connection.execute(sql, conversation_id, normalized_owner, *normalized_recipients)

    async def list_shared_with_me(
        self,
        user_identifiers: Sequence[str],
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List conversations shared with any of ``user_identifiers``, newest first."""
        identifiers = _coerce_identifiers(user_identifiers)
        if not identifiers:
            return []

        await self._init_db()

        n = len(identifiers)
        in_list = self._placeholders(n, start=1)
        limit_ph = self._ph(n + 1)
        offset_ph = self._ph(n + 2)
        sql = (
            f"SELECT id, conversation_id, owner_id, recipient, shared_at, hidden "  # noqa: S608
            f"FROM {self._table} "
            f"WHERE recipient IN ({in_list}) "
            f"AND hidden = {self._bool_literal(False)} "
            f"ORDER BY shared_at DESC "
            f"LIMIT {limit_ph} OFFSET {offset_ph}"
        )
        rows = await self._connection.fetch_all(sql, *identifiers, limit, offset)
        return [self._normalize_row(r) for r in rows]

    async def can_access(self, conversation_id: str, user_identifiers: Sequence[str]) -> bool:
        """Return True when any of ``user_identifiers`` has a visible share for ``conversation_id``."""
        identifiers = _coerce_identifiers(user_identifiers)
        if not identifiers:
            return False

        await self._init_db()

        in_list = self._placeholders(len(identifiers), start=2)
        sql = (
            f"SELECT 1 FROM {self._table} "  # noqa: S608
            f"WHERE conversation_id = {self._ph(1)} "
            f"AND recipient IN ({in_list}) "
            f"AND hidden = {self._bool_literal(False)} "
            f"LIMIT 1"
        )
        row = await self._connection.fetch_one(sql, conversation_id, *identifiers)
        return row is not None

    async def hide_share(self, conversation_id: str, user_identifiers: Sequence[str]) -> bool:
        """Soft-delete visible shares for ``conversation_id`` that match ``user_identifiers``."""
        identifiers = _coerce_identifiers(user_identifiers)
        if not identifiers:
            return False

        await self._init_db()

        in_list = self._placeholders(len(identifiers), start=2)
        sql = (
            f"UPDATE {self._table} SET hidden = {self._bool_literal(True)} "  # noqa: S608
            f"WHERE conversation_id = {self._ph(1)} "
            f"AND recipient IN ({in_list}) "
            f"AND hidden = {self._bool_literal(False)}"
        )
        rowcount = await self._connection.execute(sql, conversation_id, *identifiers)
        return rowcount > 0

    @classmethod
    def from_config(cls, config: dict) -> Self:
        """Construct the persistence from a plain config dict.

        The ``connection`` key is expected to be an
        :class:`ObjectConstructionConfig` describing a
        :class:`DatabaseConnection`, e.g.::

            {
                "connection": {
                    "type": "ragbits.core.storage.connections:SQLiteConnection",
                    "config": {"db_path": ":memory:"},
                }
            }
        """
        connection_options = ObjectConstructionConfig.model_validate(config["connection"])
        config["connection"] = DatabaseConnection.subclass_from_config(connection_options)
        return cls(**config)


# Backwards-compatible alias kept while downstream code migrates to the
# explicit ``SQLSharePersistence`` name.
SharePersistence = SQLSharePersistence
