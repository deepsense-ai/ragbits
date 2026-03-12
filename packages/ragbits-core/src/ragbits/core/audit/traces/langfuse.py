from typing import Any, Literal

from langfuse import Langfuse
from langfuse.client import StatefulSpanClient, StatefulTraceClient

from ragbits.core.audit.traces.base import TraceHandler, format_attributes


class LangfuseSpan:
    """
    Langfuse Span wrapper for trace hierarchy management.

    Wraps either a StatefulTraceClient (root) or StatefulSpanClient (nested)
    to provide a unified interface for the trace handler.
    """

    def __init__(
        self,
        client: StatefulTraceClient | StatefulSpanClient,
        trace: StatefulTraceClient,
        is_root: bool = False,
    ) -> None:
        """
        Initialize the Langfuse span wrapper.

        Args:
            client: The Langfuse trace or span client.
            trace: The root trace client (for creating nested spans).
            is_root: Whether this is the root trace.
        """
        self.client = client
        self.trace = trace
        self.is_root = is_root
        self._observation_id: str | None = None

        # Extract observation ID for parent reference in nested spans
        if isinstance(client, StatefulSpanClient):
            self._observation_id = client.id

    @property
    def observation_id(self) -> str | None:
        """Get the observation ID for use as parent in nested spans."""
        return self._observation_id


class LangfuseTraceHandler(TraceHandler[LangfuseSpan]):
    """
    Langfuse trace handler.

    Uses Langfuse's native tracing API to export traces.
    Configuration is done via environment variables:
    - LANGFUSE_PUBLIC_KEY: Your Langfuse public key
    - LANGFUSE_SECRET_KEY: Your Langfuse secret key
    - LANGFUSE_HOST: Langfuse host URL (optional, defaults to cloud)
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        """
        Initialize the LangfuseTraceHandler instance.

        Args:
            *args: Additional arguments passed to Langfuse client.
            **kwargs: Additional keyword arguments passed to Langfuse client.
        """
        super().__init__()
        self._langfuse = Langfuse(*args, **kwargs)

    def start(self, name: str, inputs: dict, current_span: LangfuseSpan | None = None) -> LangfuseSpan:
        """
        Log input data at the beginning of the trace.

        Args:
            name: The name of the trace/span.
            inputs: The input data.
            current_span: The current trace span (parent).

        Returns:
            The new Langfuse span wrapper.
        """
        formatted_inputs = format_attributes(inputs, prefix="inputs")

        if current_span is None:
            # Create root trace
            trace = self._langfuse.trace(name=name, input=formatted_inputs)
            return LangfuseSpan(client=trace, trace=trace, is_root=True)

        # Create nested span under the existing trace
        span = self._langfuse.span(
            trace_id=current_span.trace.id,
            parent_observation_id=current_span.observation_id,
            name=name,
            input=formatted_inputs,
        )
        return LangfuseSpan(client=span, trace=current_span.trace, is_root=False)

    def stop(self, outputs: dict, current_span: LangfuseSpan) -> None:
        """
        Log output data at the end of the trace.

        Args:
            outputs: The output data.
            current_span: The current trace span.
        """
        formatted_outputs = format_attributes(outputs, prefix="outputs")

        if current_span.is_root:
            # Update root trace with output
            current_span.client.update(output=formatted_outputs)
        else:
            # End nested span with output
            current_span.client.end(output=formatted_outputs)

        # Flush on root span completion
        if current_span.is_root:
            self._langfuse.flush()

    def error(self, error: Exception, current_span: LangfuseSpan) -> None:
        """
        Log error during the trace.

        Args:
            error: The error that occurred.
            current_span: The current trace span.
        """
        error_data = format_attributes({"message": str(error), "type": type(error).__name__}, prefix="error")
        level: Literal["ERROR"] = "ERROR"

        if current_span.is_root:
            # Update root trace with error
            current_span.client.update(output=error_data, metadata={"error": True})
        else:
            # End nested span with error
            current_span.client.end(output=error_data, level=level, status_message=str(error))

        # Flush on root span completion
        if current_span.is_root:
            self._langfuse.flush()
