from abc import ABC, abstractmethod
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from types import SimpleNamespace
from typing import Any, Generic, TypeVar

SpanT = TypeVar("SpanT")


class TraceHandler(Generic[SpanT], ABC):
    """
    Base class for all trace handlers.
    """

    def __init__(self) -> None:
        """
        Constructs a new TraceHandler instance.
        """
        super().__init__()
        self._spans = ContextVar[list[SpanT]]("_spans")
        self._spans.set([])

    @abstractmethod
    def start(self, name: str, inputs: dict, current_span: SpanT | None = None) -> SpanT:
        """
        Log input data at the beginning of the trace.

        Args:
            name: The name of the trace.
            inputs: The input data.
            current_span: The current trace span.

        Returns:
            The updated current trace span.
        """

    @abstractmethod
    def stop(self, outputs: dict, current_span: SpanT) -> None:
        """
        Log output data at the end of the trace.

        Args:
            outputs: The output data.
            current_span: The current trace span.
        """

    @abstractmethod
    def error(self, error: Exception, current_span: SpanT) -> None:
        """
        Log error during the trace.

        Args:
            error: The error that occurred.
            current_span: The current trace span.
        """

    @contextmanager
    def trace(self, name: str, **inputs: Any) -> Iterator[SimpleNamespace]:  # noqa: ANN401
        """
        Context manager for processing a trace.

        Args:
            name: The name of the trace.
            inputs: The input data.

        Yields:
            The output data.
        """
        self._spans.set(self._spans.get()[:])
        current_span = self._spans.get()[-1] if self._spans.get() else None

        span = self.start(
            name=name,
            inputs=inputs,
            current_span=current_span,
        )
        self._spans.get().append(span)

        try:
            yield (outputs := SimpleNamespace())
        except Exception as exc:
            span = self._spans.get().pop()
            self.error(error=exc, current_span=span)
            raise exc

        span = self._spans.get().pop()
        self.stop(outputs=vars(outputs), current_span=span)


# TODO: check do we need this method.


def simple_format_attributes(data: dict, prefix: str | None = None) -> dict:
    """
    Format attributes for CLI.

    Args:
        data: The data to format.
        prefix: The prefix to use for the keys.

    Returns:
        The formatted attributes.
    """
    flattened = {}

    for key, value in data.items():
        current_key = f"{prefix}.{key}" if prefix else key

        if isinstance(value, dict):
            flattened.update(simple_format_attributes(value, current_key))
        elif isinstance(value, list | tuple):
            flattened[current_key] = repr(
                [
                    item if isinstance(item, str | float | int | bool) else repr(item)
                    for item in value  # type: ignore
                ]
            )
        elif isinstance(value, str | float | int | bool):
            flattened[current_key] = value
        else:
            flattened[current_key] = repr(value)

    return flattened


class AttributeFormatter:
    """
    Class for formatting attributes.
    """

    max_string_length = 150
    max_list_length = 15
    opt_list_length = 4
    prompt_keywords = ["messages", "response", "conversation"]

    def __init__(self, data: dict[str, Any], prefix: str | None = None) -> None:
        """
        Initialize the attribute formatter.

        Args:
            data: The data to format.
            prefix: The prefix to use for the keys.
        """
        self.data = data
        self.prefix = prefix
        self.flattened: dict[str, str | float | int | bool | None] = {}

    def format_attributes(self, attr_dict: dict[str, Any] | None = None, curr_key: str | None = None) -> None:
        """
        Format attributes for CLI
        Args:
        attr_dict: The data to format.
        curr_key: The prefix to use for the keys.
        """
        if not curr_key and self.prefix:
            curr_key = self.prefix
        if attr_dict is None:
            attr_dict = self.data
        for key, value in attr_dict.items():
            prefix = f"{curr_key}.{key}" if curr_key else key
            self.process_item(value, prefix)

    def process_item(self, item: object, curr_key: str) -> None:
        """
        Process any type of item.

        Args:
            item: The item to process.
            curr_key: The prefix of the current item in flattened dictionary.
        """
        if isinstance(item, int | float | bool) or item is None:
            self.flattened[curr_key] = item
        elif isinstance(item, str):
            self.flattened[curr_key] = self.shorten_string(item) if not self.is_key_excluded(curr_key) else item
        elif isinstance(item, list | tuple):
            if item == []:
                self.flattened[curr_key] = repr(item)
            else:
                self.process_list(item, curr_key)
        elif isinstance(item, dict):
            if item != {}:
                self.format_attributes(item, curr_key)
            else:
                self.flattened[curr_key] = repr(item)
        else:
            self.process_object(item, curr_key)

    def process_object(self, obj: object, curr_key: str) -> None:
        """
        Process any object and it's attributes.

        Args:
            obj: The object to process.
            curr_key: the prefix of the key in flattened dictionary.
        """
        curr_key = curr_key + "." + str(type(obj).__name__)
        if not hasattr(obj, "__dict__"):
            self.flattened[curr_key] = repr(obj)
            return
        for k, v in obj.__dict__.items():
            sub_key = curr_key + "." + k
            self.process_item(v, sub_key)

    def process_list(self, lst: list | tuple, curr_key: str) -> None:
        """
        Process list by elements. If the list is too long, it will be truncated.

        Args:
            lst: The list to process.
            curr_key: the prefix of the key in flattened dictionary.
        """
        if all(isinstance(item, str | float | int | bool) for item in lst):
            self.flattened[curr_key] = repr(self.shorten_list(lst))
        elif len(lst) < self.max_list_length and len(repr(lst)) < self.max_string_length:
            self.flattened[curr_key] = repr(lst)
        else:
            is_too_long = False
            if len(lst) > self.max_list_length:
                is_too_long = True
                length = len(lst)
                last = lst[-1]
                lst = lst[: self.opt_list_length]

            for idx, item in enumerate(lst):
                position_key = f"{curr_key}[{idx}]"
                self.process_item(item, position_key)

            if is_too_long:
                position_key = f"{curr_key}[{self.opt_list_length}:{length - 1}]"
                self.flattened[position_key] = f"...{length - self.opt_list_length - 1} more elements..."
                position_key = f"{curr_key}[{length - 1}]"
                self.process_item(last, position_key)

    def shorten_list(self, lst: list | tuple) -> list:
        """
        Shortens a list if it's longer than 3 elements. Shortens list elements if it's long string.

        Args:
            lst: The list to shorten.

        Returns:
            shortened list.
        """
        lst = [self.shorten_string(item) if isinstance(item, str) else item for item in lst]
        if len(lst) > self.opt_list_length:
            return lst[: self.opt_list_length - 1] + ["..."] + [lst[-1]]

        return lst

    def shorten_string(self, string: str) -> str:
        """
        Shortens string if it's longer than max_string_length.

        Args:
            string: The string to shorten.

        Returns:
            shortened string.
        """
        if len(string) > self.max_string_length:
            return string[: self.max_string_length] + "..."
        return string

    def is_key_excluded(self, curr_key: str) -> bool:
        """
        Check if a key belongs to the prompt keywords list - which means that the string should not be truncated
        Args:
            curr_key: The current key in flattened dictionary.

        Returns:
            bool: True if the key is excluded.
        """
        return any(keyword in curr_key for keyword in self.prompt_keywords)
