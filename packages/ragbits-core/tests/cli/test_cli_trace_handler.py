import os

import typer
from typer.testing import CliRunner

from ragbits.cli import app as root_app
from ragbits.core.audit.traces import clear_trace_handlers, set_trace_handlers, traceable

PROCESS_1_STR = "inputs.a: 4\ninputs.b: 2\noutputs.returned: 7"
PROCESS_2_STR = "inputs.a: 5\n    inputs.b: 2\n    outputs.returned: 7"
PROCESS_NAME_STR = "add_numbers: 0"

mock_app = typer.Typer(no_args_is_help=True)
root_app.add_typer(mock_app, name="mock")


@mock_app.command()
@traceable
def add_numbers(a: int, b: int) -> int:
    if a % 2 == 0:
        return add_numbers(a + 1, b)
    return a + b


def test_add_numbers_cli_trace_handler_with_verbose():
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(root_app, ["--verbose", "mock", "add-numbers", "4", "2"])
    if os.getenv("RAGBITS_VERBOSE"):
        assert os.getenv("RAGBITS_VERBOSE") == "0", "Should run test with RAGBITS_VERBOSE=0"
    assert result.exit_code == 0
    assert PROCESS_1_STR in result.stdout
    assert PROCESS_2_STR in result.stdout
    assert PROCESS_NAME_STR in result.stdout
    clear_trace_handlers()


def test_add_numbers_cli_trace_handler_with_set_cli():
    set_trace_handlers("cli")
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(root_app, ["mock", "add-numbers", "4", "2"])
    if os.getenv("RAGBITS_VERBOSE"):
        assert os.getenv("RAGBITS_VERBOSE") == "0", "Should run test with RAGBITS_VERBOSE=0"
    assert result.exit_code == 0
    assert PROCESS_1_STR in result.stdout
    assert PROCESS_2_STR in result.stdout
    assert PROCESS_NAME_STR in result.stdout
    clear_trace_handlers()


def test_no_cli_trace_handler():
    clear_trace_handlers()
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(root_app, ["mock", "add-numbers", "4", "2"])
    if os.getenv("RAGBITS_VERBOSE"):
        assert os.getenv("RAGBITS_VERBOSE") == "0", "Should run test with RAGBITS_VERBOSE=0"
    assert result.exit_code == 0
    assert PROCESS_1_STR not in result.stdout
    assert PROCESS_2_STR not in result.stdout
    assert PROCESS_NAME_STR not in result.stdout
