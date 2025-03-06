from abc import ABC, abstractmethod
from collections.abc import Iterator, Sequence
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


class AttributeFormatter:
    """
    Class for formatting attributes.
    """

    max_string_length = 150
    max_list_length = 15
    opt_list_length = 2
    max_recurrence_depth = 4

    user_prompt_keywords = ["system_prompt", "rendered_system_prompt"]
    system_prompt_keywords = ["user_prompt", "rendered_user_prompt"]
    response_keywords = ["response"]

    def __init__(self, data: dict[str, Any], prefix: str | None = None) -> None:
        """
        Initialize the attribute formatter.

        Args:
            data: The data to format.
            prefix: The prefix to use for the keys.
        """
        self.data = data
        self.prefix = prefix
        self.flattened: dict[
            str, str | float | int | bool | Sequence[str] | Sequence[bool] | Sequence[int] | Sequence[float]
        ] = {}

    def process_attributes(
        self, attr_dict: dict[str, Any] | None = None, curr_key: str | None = None, recurrence: int = 0
    ) -> None:
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
            self.process_item(value, prefix, recurrence)

    def process_item(self, item: object, curr_key: str, recurrence: int) -> None:
        """
        Process any type of item.

        Args:
            item: The item to process.
            curr_key: The prefix of the current item in flattened dictionary.
            recurrence: The level of recursion.
        """
        # if self.is_special_key(curr_key, self.excluded):
        #     return
        special_keywords = self.user_prompt_keywords + self.system_prompt_keywords + self.response_keywords
        recurrence += 1

        if recurrence > self.max_recurrence_depth:
            self.flattened[curr_key] = repr(item)
            return

        if isinstance(item, int | float | bool):
            self.flattened[curr_key] = item
        elif isinstance(item, str):
            self.flattened[curr_key] = (
                self.shorten_string(item) if not self.is_special_key(curr_key, special_keywords) else item
            )
        elif item is None:
            self.flattened[curr_key] = repr(None)
        elif isinstance(item, list | tuple | set):
            if item == []:
                self.flattened[curr_key] = repr(item)
            else:
                self.process_list(item, curr_key, recurrence)
        elif isinstance(item, dict):
            if item != {}:
                self.process_attributes(item, curr_key)
            else:
                self.flattened[curr_key] = repr(item)
        else:
            self.process_object(item, curr_key, recurrence)

    def process_object(self, obj: object, curr_key: str, recurrence: int) -> None:
        """
        Process any object and it's attributes.

        Args:
            obj: The object to process.
            curr_key: the prefix of the key in flattened dictionary.
            recurrence: the level of depth for recursion.
        """
        recurrence += 1
        if recurrence > self.max_recurrence_depth:
            self.flattened[curr_key] = repr(obj)
            return
        curr_key = curr_key + "." + str(type(obj).__name__)

        if not hasattr(obj, "__dict__") or obj.__dict__ == {}:
            self.flattened[curr_key] = repr(obj)
            return
        for k, v in obj.__dict__.items():
            if k.startswith("__"):
                pass
            elif k.startswith("_"):
                self.flattened[curr_key] = repr(v)
            else:
                sub_key = curr_key + "." + k
                self.process_item(v, sub_key, recurrence)

    def process_list(self, lst: list | tuple | set, curr_key: str, recurrence: int) -> None:
        """
        Process list by elements. If the list is too long, it will be truncated.

        Args:
            lst: The list to process.
            curr_key: the prefix of the key in flattened dictionary.
            recurrence: the depth level of iterating over the objects.
        """
        if isinstance(lst, set):
            lst = list(lst)
        list_length = len(lst)
        if all(isinstance(item, str | float | int | bool) for item in lst):
            self.flattened[curr_key] = self.shorten_list(lst)
        elif list_length < self.max_list_length and len(repr(lst)) < self.max_string_length:
            self.flattened[curr_key] = repr(lst)
        else:
            is_too_long = False
            if list_length > self.max_list_length:
                is_too_long = True
                last = lst[-1]
                lst = lst[: self.opt_list_length]

            for idx, item in enumerate(lst):
                position_key = f"{curr_key}[{idx}]"
                self.process_item(item, position_key, recurrence)

            if is_too_long:
                position_key = f"{curr_key}[{self.opt_list_length}:{list_length - 1}]"
                self.flattened[position_key] = f"...{list_length - self.opt_list_length - 1} more elements..."
                position_key = f"{curr_key}[{list_length - 1}]"
                self.process_item(last, position_key, recurrence)

    @classmethod
    def shorten_list(cls, lst: list | tuple | set) -> str:
        """
        Shortens a list if it's longer than 3 elements. Shortens list elements if it's long string.

        Args:
            lst: The list to shorten.

        Returns:
            string representation of shortened list.
        """
        lst = [cls.shorten_string(item) if isinstance(item, str) else item for item in lst]
        list_length = len(lst)
        if list_length > cls.max_list_length:
            return str(lst[: cls.opt_list_length - 1] + ["..."] + [lst[-1]]) + f"(total {list_length} elements)"

        return str(lst)

    @classmethod
    def shorten_string(cls, string: str) -> str:
        """
        Shortens string if it's longer than max_string_length.

        Args:
            string: The string to shorten.

        Returns:
            shortened string.
        """
        if len(string) > cls.max_string_length:
            return string[: cls.max_string_length] + "..."
        return string

    @classmethod
    def is_special_key(cls, curr_key: str, key_list: list[str]) -> bool:
        """
        Check if a key belongs to the prompt keywords list - which means that the string should not be truncated
        Args:
            curr_key: The current key in flattened dictionary.
            key_list: The list of keys to check.

        Returns:
            bool: True if the key is excluded.
        """
        return any(keyword == curr_key.split(".")[-1] for keyword in key_list)


def format_attributes(data: dict, prefix: str | None = None) -> dict:
    """
    Format attributes for open telemetry tracing.

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
