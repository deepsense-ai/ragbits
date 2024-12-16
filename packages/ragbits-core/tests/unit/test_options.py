import pytest

from ragbits.core.options import Options
from ragbits.core.types import NOT_GIVEN, NotGiven


class OptionA(Options):
    a: int = 1
    d: int | NotGiven = NOT_GIVEN


class OptionsB(Options):
    b: int = 2
    e: int | None = None


class OptionsC(Options):
    a: int = 2
    c: str = "c"


@pytest.mark.parametrize(
    ("options", "expected"),
    [
        (OptionA(), {"a": 1, "d": None}),
        (OptionsB(), {"b": 2, "e": None}),
    ],
)
def test_default_options(options: Options, expected: dict) -> None:
    assert options.dict() == expected


def test_merge_options() -> None:
    options_a = OptionA()
    options_b = OptionsB()
    options_c = OptionsC()

    merged = options_a | options_b | options_c

    assert merged.dict() == {"a": 2, "b": 2, "c": "c", "d": None, "e": None}
