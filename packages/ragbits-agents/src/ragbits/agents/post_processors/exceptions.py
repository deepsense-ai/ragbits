class SupervisorMaxRetriesExceededError(Exception):
    """Raised when SupervisorPostProcessor exceeds the maximum number of retries."""

    def __init__(self, max_retries: int, last_validations: list | None = None) -> None:
        self.max_retries = max_retries
        self.last_validations = last_validations or []
        super().__init__(f"Supervisor: maximum retries ({max_retries}) exceeded.")


class SupervisorCorrectionPromptFormatError(Exception):
    """Raised when SupervisorPostProcessor cannot format the correction prompt."""

    def __init__(self, missing_keys: list[str] | None = None, original_error: Exception | None = None) -> None:
        self.missing_keys = missing_keys or []
        self.original_error = original_error
        details = f" Missing keys: {', '.join(self.missing_keys)}." if self.missing_keys else ""
        super().__init__(f"Supervisor: failed to format correction prompt.{details}")
