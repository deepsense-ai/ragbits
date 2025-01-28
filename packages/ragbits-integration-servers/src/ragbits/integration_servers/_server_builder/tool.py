from typing import Any

from pydantic import BaseModel


class Tool(BaseModel):
    backend: Any
    name: str | None
    description: str | None
