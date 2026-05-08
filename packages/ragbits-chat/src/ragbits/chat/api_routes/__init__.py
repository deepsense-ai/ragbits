"""FastAPI routers that `RagbitsAPI` composes.

Extracting routes into routers keeps the main ``RagbitsAPI`` class focused on
wiring (middleware, dependencies, lifespan) and makes individual feature
groups importable and unit-testable on their own.
"""

from ragbits.chat.api_routes.conversations import build_conversations_router, build_share_router

__all__ = ["build_conversations_router", "build_share_router"]
