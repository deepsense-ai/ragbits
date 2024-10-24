# pylint: disable=missing-function-docstring,missing-return-doc

import asyncio
from collections.abc import Callable
from functools import wraps
from importlib.util import find_spec
from typing import ParamSpec, TypeVar

_P = ParamSpec("_P")
_T = TypeVar("_T")


def requires_dependencies(
    dependencies: str | list[str],
    extras: str | None = None,
) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]:
    """
    Decorator to check if the dependencies are installed before running the function.

    Args:
        dependencies: The dependencies to check.
        extras: The extras to install.

    Returns:
        The decorated function.
    """
    if isinstance(dependencies, str):
        dependencies = [dependencies]

    def decorator(func: Callable[_P, _T]) -> Callable[_P, _T]:
        def run_check() -> None:
            missing_dependencies = [dependency for dependency in dependencies if not find_spec(dependency)]
            if len(missing_dependencies) > 0:
                missing_deps = ", ".join(missing_dependencies)
                install_cmd = (
                    f"pip install 'ragbits[{extras}]'" if extras else f"pip install {' '.join(missing_dependencies)}"
                )
                raise ImportError(
                    f"Following dependencies are missing: {missing_deps}. Please install them using `{install_cmd}`."
                )

        @wraps(func)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _T:
            run_check()
            return func(*args, **kwargs)

        @wraps(func)
        async def wrapper_async(*args: _P.args, **kwargs: _P.kwargs) -> _T:
            run_check()
            return await func(*args, **kwargs)  # type: ignore

        if asyncio.iscoroutinefunction(func):
            return wrapper_async  # type: ignore
        return wrapper

    return decorator
