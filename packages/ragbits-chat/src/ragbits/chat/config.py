import os

# Environment-aware cookie security: only require HTTPS in production
IS_PRODUCTION = os.getenv("RAGBITS_ENVIRONMENT", "").lower() in ("production", "prod")

# Session cookie name - used for storing session ID in HTTP-only cookie
SESSION_COOKIE_NAME = os.getenv("RAGBITS_COOKIE", "ragbits_session")

BASE_URL = os.getenv("RAGBITS_BASE_URL", "http://localhost:8000").rstrip("/")

# Chunk size for large base64 images to prevent SSE message size issues
# Keep chunks extremely small to avoid JSON string length limits in browsers and SSE parsing issues
# Account for JSON overhead: metadata + base64 data should fit comfortably in browser limits
CHUNK_SIZE = 102400  # ~100KB bytes base64 chunks for ultra-safe JSON parsing and SSE transmissio
