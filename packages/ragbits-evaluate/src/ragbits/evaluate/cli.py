import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer
from pydantic import BaseModel

from ragbits.core.utils.config_handling import WithConstructionConfig
from ragbits.cli._utils import get_instance_or_exit
from ragbits.cli.state import print_output
from ragbits.document_search import DocumentSearch
from ragbits.evaluate.config import eval_config
from ragbits.evaluate.dataloaders.base import DataLoader
from ragbits.evaluate.evaluation_target import EvaluationTarget
from ragbits.evaluate.evaluator import Evaluator
from ragbits.evaluate.metrics.base import MetricSet
from ragbits.evaluate.pipelines.document_search import DocumentSearchPipeline

eval_app = typer.Typer(no_args_is_help=True)


def register(app: typer.Typer) -> None:
    """
    Register the CLI commands for the package.

    Args:
        app: The Typer object to register the commands with.
    """
    app.add_typer(eval_app, name="evaluate", help="Commands for interacting with ragbits evaluate module")


@dataclass
class _CLIState:
    evaluation_target: WithConstructionConfig | None = None
    metrics: MetricSet | None = None
    dataloader: DataLoader | None = None



class EvaluationResult(BaseModel):
    """A container for evaluation results"""

    metrics: dict


state: _CLIState = _CLIState()


@eval_app.callback()
def common_args(
    target_factory_path: Annotated[
        str | None,
        typer.Option(
            help="Path to a factory of the document search pipeline in format: python.path:function_name",
            exists=True,
            resolve_path=True,
        ),
    ] = None,
    target_yaml_path: Annotated[
        Path | None,
        typer.Option(
            help="Path to a YAML configuration file of the document search pipeline", exists=True, resolve_path=True
        ),
    ] = None,
) -> None:
    """
    Common arguments for the evaluate commands.
    """
    state.document_search = get_instance_or_exit(
        DocumentSearch,
        factory_path=target_factory_path,
        yaml_path=target_yaml_path,
    )
    state.evaluation_target = get_instance_or_exit(
        EvaluationTarget, factory_path=target_factory_path, yaml_path=target_yaml_path, config_override=eval_config
    )


@eval_app.command()
def run_evaluation() -> None:
    """
    Evaluate the set up pipeline.
    """

    async def run() -> None:
        if state.document_search is None:
            raise ValueError("Document search not initialized")
        if state.evaluation_target is None:
            raise ValueError("Evaluation target not initialized")
        evaluation_pipeline = DocumentSearchPipeline(document_search=state.document_search)
        evaluator = Evaluator()
        metric_results = await evaluator.compute(
            pipeline=evaluation_pipeline,
            metrics=state.evaluation_target.metrics,
            dataloader=state.evaluation_target.dataloader,
        )
        evaluation_results = EvaluationResult(
            metrics={"metrics": metric_results["metrics"], "time_perf": metric_results["time_perf"]}
        )
        print_output(evaluation_results)

    asyncio.run(run())
