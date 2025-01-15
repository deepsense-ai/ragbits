import os

from typer.testing import CliRunner

from ragbits.cli import app as root_app
from ragbits.cli import autoregister
from ragbits.core import audit

PROCESS_NAME_STR = "InMemoryVectorStore.store: 0.000s\n"
INPUTS_1_STR = "inputs.entries: [\"VectorStoreEntry(id='1', key='entry 1', vector=[4.0, 5.0]"
OUTPUTS_1_STR = "outputs.returned: [\"VectorStoreEntry(id='1', key='entry 1', vector=[4.0, 5.0]"


def test_no_cli_trace_handler():
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        root_app,
        [
            "--output",
            "json",
            "vector-store",
            "--factory-pathcli.test_vector_store:vector_store_factory",
            "list",
        ],
        env={"RAGBITS_VERBOSE": "1"},
    )

    if os.getenv("RAGBITS_VERBOSE"):
        assert os.getenv("RAGBITS_VERBOSE") == "0"
    audit.clear_event_handlers()
    assert PROCESS_NAME_STR not in result.stdout
    assert INPUTS_1_STR not in result.stdout
    assert OUTPUTS_1_STR not in result.stdout
    assert result.exit_code == 0


def test_set_cli_trace_handler():
    autoregister()
    audit.set_trace_handlers("cli")
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        root_app,
        [
            "--output",
            "json",
            "vector-store",
            "--factory-path",
            "cli.test_vector_store:vector_store_factory",
            "list",
        ],
    )
    if os.getenv("RAGBITS_VERBOSE"):
        assert os.getenv("RAGBITS_VERBOSE") == "0"

    audit.clear_event_handlers()
    assert PROCESS_NAME_STR in result.stdout
    assert INPUTS_1_STR in result.stdout
    assert OUTPUTS_1_STR in result.stdout
    assert result.exit_code == 0


def test_cli_trace_handler_from_verbose():
    autoregister()
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        root_app,
        [
            "--verbose",
            "--output",
            "json",
            "vector-store",
            "--factory-path",
            "cli.test_vector_store:vector_store_factory",
            "list",
        ],
    )
    if os.getenv("RAGBITS_VERBOSE"):
        assert os.getenv("RAGBITS_VERBOSE") == "0"
    audit.clear_event_handlers()
    assert PROCESS_NAME_STR in result.stdout
    assert INPUTS_1_STR in result.stdout
    assert OUTPUTS_1_STR in result.stdout
    assert result.exit_code == 0
