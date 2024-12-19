from abc import ABC
from typing import Any, ClassVar, TypeVar

from pydantic import BaseModel, ConfigDict
from typing_extensions import Self

from ragbits.core.types import NotGiven

OptionsT = TypeVar("OptionsT", bound="Options")


class Options(BaseModel, ABC):
    """
    A dataclass that represents all available options. Thanks to the extra='allow' configuration, it allows for
    additional fields that are not defined in the class.
    """

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)
    _not_given: ClassVar[Any] = None

    def __or__(self, other: "Options") -> Self:
        """
        Merges two Options, prioritizing non-NOT_GIVEN values from the 'other' object.
        """
        self_dict = self.model_dump()
        other_dict = other.model_dump()

        updated_dict = {
            key: other_dict[key]
            if not isinstance(other_dict.get(key), NotGiven) and key in other_dict
            else self_dict[key]
            for key in self_dict.keys() | other_dict.keys()
        }

        return self.__class__(**updated_dict)

    def dict(self) -> dict[str, Any]:  # type: ignore # mypy complains about overriding BaseModel.dict
        """
        Creates a dictionary representation of the Options instance.
        If a value is None, it will be replaced with a provider-specific not-given sentinel.

        Returns:
            A dictionary representation of the Options instance.
        """
        options = self.model_dump()

        return {
            key: self._not_given if value is None or isinstance(value, NotGiven) else value
            for key, value in options.items()
        }
