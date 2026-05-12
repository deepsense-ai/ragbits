from typing import Any

from pydantic import BaseModel

from ragbits.agents.tool import Tool


class User(BaseModel):
    name: str
    age: int


def add_user(user: User, other_argument: int) -> dict[str, Any]:
    """Adds a user to a database"""
    return {"status": "OK", "user": user}


def test_pydantic_model_argument_is_instantiated():
    """The LLM sends a plain dict; the callable must receive a User instance."""
    tool = Tool.from_callable(add_user)
    tool_output = tool.on_tool_call({"name": "user", "age": 10}, 17)
    assert tool_output["status"] == "OK"
    assert tool_output["user"].name == "user"
