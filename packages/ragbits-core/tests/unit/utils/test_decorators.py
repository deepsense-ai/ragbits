import pytest

from ragbits.core.utils.decorators import requires_dependencies


def test_single_dependency_installed() -> None:
    @requires_dependencies("pytest")
    def some_function() -> str:
        return "success"

    assert some_function() == "success"


def test_single_dependency_missing() -> None:
    @requires_dependencies("nonexistent_dependency")
    def some_function() -> str:
        return "success"

    with pytest.raises(ImportError) as exc:
        some_function()

    assert (
        str(exc.value) == "Following dependencies are missing: nonexistent_dependency."
        " Please install them using `pip install nonexistent_dependency`."
    )


def test_multiple_dependencies_installed() -> None:
    @requires_dependencies(["pytest", "asyncio"])
    def some_function() -> str:
        return "success"

    assert some_function() == "success"


def test_multiple_dependencies_some_missing() -> None:
    @requires_dependencies(["pytest", "nonexistent_dependency"])
    def some_function() -> str:
        return "success"

    with pytest.raises(ImportError) as exc:
        some_function()

    assert (
        str(exc.value) == "Following dependencies are missing: nonexistent_dependency."
        " Please install them using `pip install nonexistent_dependency`."
    )
