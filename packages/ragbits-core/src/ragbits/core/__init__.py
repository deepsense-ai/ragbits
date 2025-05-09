import os

import typer

from ragbits.core.audit.traces import set_trace_handlers
from ragbits.core.config import import_modules_from_config

if os.getenv("RAGBITS_VERBOSE", "0") == "1":
    typer.echo('Verbose mode is enabled with environment variable "RAGBITS_VERBOSE".')
    set_trace_handlers("cli")

import_modules_from_config()
