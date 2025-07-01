from typing import Any

import logfire

from ragbits.core.audit.traces.otel import OtelTraceHandler


class LogfireTraceHandler(OtelTraceHandler):
    """
    Logfire trace handler.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        """
        Initialize the LogfireTraceHandler instance.
        """
        logfire.configure(*args, **kwargs)
        super().__init__()
