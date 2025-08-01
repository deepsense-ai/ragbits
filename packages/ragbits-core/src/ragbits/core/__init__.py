import os
from concurrent.futures import ThreadPoolExecutor

import typer

from ragbits.core.audit.traces import set_trace_handlers

_config_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="config-import")
_config_future = None


def _import_and_run_config() -> None:
    from ragbits.core.config import import_modules_from_config

    import_modules_from_config()


def ensure_config_loaded() -> None:
    """Wait for config import to complete if it hasn't already."""
    if _config_future:
        _config_future.result()


if os.getenv("RAGBITS_VERBOSE", "0") == "1":
    typer.echo('Verbose mode is enabled with environment variable "RAGBITS_VERBOSE".')
    set_trace_handlers("cli")

_config_future = _config_executor.submit(_import_and_run_config)
