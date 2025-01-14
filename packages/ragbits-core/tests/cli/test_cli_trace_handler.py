import os
from unittest.mock import patch

from typer.testing import CliRunner

from ragbits.cli import app as root_app
from ragbits.cli import autoregister
from ragbits.core import audit

PROCESS_NAME_STR = "InMemoryVectorStore.store Status: completed; Duration: "
INPUTS_1_STR = "entries: [VectorStoreEntry(id='1', key='entry 1', vector=[4.0, 5.0]"
OUTPUTS_1_STR = "returned: [VectorStoreEntry(id='1', key='entry 1', vector=[4.0, 5.0]"


def test_no_cli_trace_handler():
    with patch.dict(os.environ, {"RAGBITS_VERBOSE": "0"}):
        autoregister()
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
            env={"RAGBITS_VERBOSE": "0"},
        )

        if os.getenv("RAGBITS_VERBOSE"):
            assert os.getenv("RAGBITS_VERBOSE") == "0"
        assert PROCESS_NAME_STR not in result.stdout
        assert INPUTS_1_STR not in result.stdout
        assert OUTPUTS_1_STR not in result.stdout
        assert result.exit_code == 0


def test_set_cli_trace_handler():
    with patch.dict(os.environ, {"RAGBITS_VERBOSE": "0"}):
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
        assert PROCESS_NAME_STR in result.stdout
        assert INPUTS_1_STR in result.stdout
        assert OUTPUTS_1_STR in result.stdout
        assert result.exit_code == 0


def test_cli_trace_handler_from_verbose():
    with patch.dict(os.environ, {"RAGBITS_VERBOSE": "0"}):
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
        assert PROCESS_NAME_STR in result.stdout
        assert INPUTS_1_STR in result.stdout
        assert OUTPUTS_1_STR in result.stdout
        assert result.exit_code == 0
