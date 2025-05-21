import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer
from pydantic import BaseModel

from ragbits.cli._utils import get_instance_or_exit
from ragbits.cli.state import print_output
from ragbits.core.utils.config_handling import WithConstructionConfig
from ragbits.evaluate.config import eval_config
from ragbits.evaluate.dataloaders import DataLoader
from ragbits.evaluate.evaluator import Evaluator
from ragbits.evaluate.metrics.base import MetricSet
from ragbits.evaluate.pipelines import get_evaluation_pipeline_for_target
from ragbits.evaluate.pipelines.base import EvaluationPipeline

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
    dataloader: DataLoader | None = None
    pipeline: EvaluationPipeline | None = None
    metrics: MetricSet | None = None


class EvaluationResult(BaseModel):
    """A container for evaluation results"""

    metrics: dict


state: _CLIState = _CLIState()


@eval_app.callback()
def common_args(
    dataloader_factory_path: Annotated[
        str | None,
        typer.Option(
            help="A path to evaluation data loader factory in format python.path:function_name",
            exists=True,
            resolve_path=True,
        ),
    ] = None,
    dataloader_yaml_path: Annotated[
        Path | None,
        typer.Option(
            help="A path to evaluation data loader configuration",
            exists=True,
            resolve_path=True,
        ),
    ] = None,
    target_factory_path: Annotated[
        str | None,
        typer.Option(
            help="A path to a factory of the evaluation target class in format: python.path:function_name",
            exists=True,
            resolve_path=True,
        ),
    ] = None,
    target_yaml_path: Annotated[
        Path | None,
        typer.Option(
            help="A path to a YAML configuration file of the evaluation target class",
            exists=True,
            resolve_path=True,
        ),
    ] = None,
    metrics_factory_path: Annotated[
        str | None,
        typer.Option(
            help="A path to metrics factory in format python.path:function_name",
            exists=True,
            resolve_path=True,
        ),
    ] = None,
    metrics_yaml_path: Annotated[
        Path | None,
        typer.Option(
            help="A path to metrics configuration",
            exists=True,
            resolve_path=True,
        ),
    ] = None,
) -> None:
    """
    Common arguments for the evaluate commands.
    """
    evaluation_target = get_instance_or_exit(
        cls=WithConstructionConfig,
        factory_path=target_factory_path,
        yaml_path=target_yaml_path,
        config_override=eval_config,
    )
    state.pipeline = get_evaluation_pipeline_for_target(evaluation_target)
    # TODO: validate if given dataloader is suitable for evaluation pipeline
    state.dataloader = get_instance_or_exit(
        cls=DataLoader,
        factory_path=dataloader_factory_path,
        yaml_path=dataloader_yaml_path,
        config_override=eval_config,
    )
    # TODO: validate if given metric set is suitable for evaluation pipeline
    state.metrics = get_instance_or_exit(
        cls=MetricSet,
        factory_path=metrics_factory_path,
        yaml_path=metrics_yaml_path,
        config_override=eval_config,
    )


@eval_app.command()
def run() -> None:
    """
    Evaluate the pipeline.
    """

    async def run() -> None:
        if state.dataloader is None:
            raise ValueError("Evaluation dataloader not initialized")
        if state.pipeline is None:
            raise ValueError("Evaluation pipeline not initialized")
        if state.metrics is None:
            raise ValueError("Evaluation metrics not initialized")

        evaluator = Evaluator()
        metric_results = await evaluator.compute(
            pipeline=state.pipeline,
            dataloader=state.dataloader,
            metricset=state.metrics,
        )
        evaluation_results = EvaluationResult(
            metrics={"metrics": metric_results.metrics, "time_perf": metric_results.time_perf}
        )
        print_output(evaluation_results)

    asyncio.run(run())
