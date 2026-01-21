"""
Output types for hook callbacks.
"""

from typing import Any, Literal

from pydantic import BaseModel, field_validator, model_validator


class PreToolOutput(BaseModel):
    """
    Output returned by pre-tool hook callbacks.

    This allows hooks to control tool execution:
    - "allow": Proceed with tool execution (default behavior)
    - "deny": Block tool execution and provide a reason
    - "modify": Execute tool with modified input

    Attributes:
        action: The action to take ("allow", "deny", or "modify")
        modified_input: Modified tool input (required when action="modify")
        denial_message: Message to return to agent (required when action="deny")
    """

    action: Literal["allow", "deny", "modify"]
    modified_input: dict[str, Any] | None = None
    denial_message: str | None = None

    @model_validator(mode="after")
    def validate_action_fields(self) -> "PreToolOutput":
        """Validate that required fields are present for each action."""
        if self.action == "modify" and self.modified_input is None:
            raise ValueError("modified_input must be provided when action='modify'")
        if self.action == "deny" and self.denial_message is None:
            raise ValueError("denial_message must be provided when action='deny'")
        return self


class PostToolOutput(BaseModel):
    """
    Output returned by post-tool hook callbacks.

    This allows hooks to modify tool results:
    - "pass": Return the original tool output unchanged
    - "modify": Return modified tool output

    Attributes:
        action: The action to take ("pass" or "modify")
        modified_output: Modified tool output (required when action="modify")
    """

    action: Literal["pass", "modify"]
    modified_output: Any = None

    @field_validator("modified_output")
    @classmethod
    def validate_modified_output(cls, v: Any, info) -> Any:
        """Validate that modified_output is provided when action='modify'."""
        if info.data.get("action") == "modify" and v is None:
            raise ValueError("modified_output must be provided when action='modify'")
        return v
