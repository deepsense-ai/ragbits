from __future__ import annotations

import json
import logging

from pydantic import TypeAdapter

from .interface.types import ChatResponse

logger = logging.getLogger(__name__)


def build_api_url(base_url: str, path: str) -> str:
    """Join *base_url* and *path* preserving exactly one slash."""
    base = base_url.rstrip("/")
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{base}{path}"


PREFIX = "data: "


def parse_sse_line(line: str) -> ChatResponse | None:
    r"""Parse a single *Server-Sent-Event* line coming from RagbitsAPI.

    Expected format:  ``data: {....json....}\n``
    Returns a *ChatResponse* instance or ``None`` if the line is not a
    data line. Parsing/validation errors are logged (and ``None`` is returned).
    """
    if not line.startswith(PREFIX):
        return None
    try:
        json_payload = line[len(PREFIX) :].strip()
        data = json.loads(json_payload)
        adapter: TypeAdapter[ChatResponse] = TypeAdapter(ChatResponse)
        return adapter.validate_python(data)
    except Exception as exc:
        logger.error("Failed to parse SSE line: %s", exc, exc_info=True)
        return None
