class SupervisorMaxRetriesExceededError(Exception):
    """Raised when SupervisorPostProcessor exceeds the maximum number of retries."""

    def __init__(self, max_retries: int, last_validations: list | None = None) -> None:
        self.max_retries = max_retries
        self.last_validations = last_validations or []
        super().__init__(f"Supervisor: maximum retries ({max_retries}) exceeded.")
