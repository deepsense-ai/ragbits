import os
from collections.abc import Iterable, Iterator
from itertools import islice
from typing import TypeVar

T = TypeVar("T")


def env_vars_not_set(env_vars: list[str]) -> bool:
    """
    Checks if no environment variable is set.

    Args:
        env_vars: The list of environment variables to check.

    Returns:
        True if no environment variable is set, otherwise False.
    """
    return all(os.environ.get(env_var) is None for env_var in env_vars)


def batched(data: Iterable[T], batch_size: int | None = None) -> Iterator[list[T]]:
    """
    Batches the data into chunks of the given size.

    Args:
        data: The data to batch.
        batch_size: The size of the batch. If None, no batching is performed.

    Returns:
        An iterator of batches of the data when batch_size is provided,
        or the original iterator when batch_size is None.
    """
    it = iter(data)
    while batch := list(islice(it, batch_size)):
        yield batch
