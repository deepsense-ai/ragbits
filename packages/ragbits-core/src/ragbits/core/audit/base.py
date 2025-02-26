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


def format_attributes_1(data: dict, prefix: str | None = None) -> dict:
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
            flattened.update(format_attributes(value, current_key))
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


max_string_length = 150
max_list_length = 15
opt_list_length = 3


def format_attributes(data: dict, prefix: str | None = None) -> dict:
    """
    Args:
    data: The data to format.
    prefix: The prefix to use for the keys.

    Returns:
        The formatted attributes.
    """

    def shorten_list(lst: list | tuple) -> list:
        """
        Shortens a list if it's longer than 3 elements. Shortens list elements if it's long string.

        Args: lst: The list to shorten.
        Returns: shortened list.
        """
        lst = [shorten_string(item) if isinstance(item, str) else item for item in lst]
        if len(lst) > opt_list_length:
            return lst[: opt_list_length - 1] + ["..."] + [lst[-1]]

        return lst

    def shorten_string(string: str) -> str:
        """
        Shortens strinf if it's longer than max_string_length.
        Args: string: The string to shorten.
        Returns: shortened string.
        """
        if len(string) > max_string_length:
            return string[:max_string_length] + "..."
        return string

    def process_item(item: object, curr_key: str, attr_dict: dict) -> None:
        """
        Process any type of item.

        Args:
            item: The item to process.
            curr_key: The prefix of the current item in flattened dictionary.
            attr_dict: Flattened dictionary of attributes.
        """
        if isinstance(item, str | int | float | bool) or item is None:
            attr_dict[curr_key] = shorten_string(item) if isinstance(item, str) else item
        elif isinstance(item, list | tuple):
            if item == []:
                attr_dict[curr_key] = repr(item)
            else:
                attr_dict.update(process_list(item, curr_key))
        elif isinstance(item, dict):
            if item == {}:
                attr_dict[curr_key] = repr(item)
            else:
                attr_dict.update(format_attributes(item, curr_key))
        else:
            attr_dict.update(process_object(item, curr_key))

    def process_object(obj: object, curr_key: str) -> dict:
        """
        Process any object and it's attributes.

        Args:
            obj: The object to process.
            curr_key: the prefix of the key in flattened dictionary.
        Returns: flattened dictionary.
        """
        obj_attr = {}
        curr_key = curr_key + "." + str(type(obj).__name__)
        if not hasattr(obj, "__dict__"):
            obj_attr[curr_key] = repr(obj)
            return obj_attr
        for k, v in obj.__dict__.items():
            sub_key = curr_key + "." + k
            process_item(v, sub_key, obj_attr)
        return obj_attr

    def process_list(lst: list | tuple, curr_key: str) -> dict:
        """
        Process lists by elements.
        Args: lst: The list to process.
        curr_key: the prefix of the key in flattened dictionary.
        Returns: flattened dictionary.
        """
        lst_attr = {}
        if all(isinstance(item, str | float | int | bool) for item in lst):
            lst_attr[curr_key] = repr(shorten_list(lst))
        elif len(lst) < max_list_length and len(repr(lst)) < max_string_length:
            lst_attr[curr_key] = repr(lst)
        else:
            for idx, item in enumerate(lst):
                position_key = f"{curr_key}[{idx}]"
                process_item(item, position_key, lst_attr)
        return lst_attr

    flattened: dict[str, str | float | int | bool] = {}

    for key, value in data.items():
        current_key = f"{prefix}.{key}" if prefix else key
        process_item(value, current_key, flattened)
    return flattened
