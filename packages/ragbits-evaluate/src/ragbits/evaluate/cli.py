import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer
from pydantic import BaseModel

from ragbits.cli._utils import get_instance_or_exit
from ragbits.cli.state import print_output
from ragbits.core.utils.config_handling import WithConstructionConfig, import_by_path
from ragbits.evaluate.config import eval_config
from ragbits.evaluate.dataloaders import DataLoader, get_dataloader_instance
from ragbits.evaluate.evaluator import Evaluator
from ragbits.evaluate.metrics.base import MetricSet
from ragbits.evaluate.pipelines import get_evaluation_pipeline_for_target

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
    target_cls: Annotated[
        str,
        typer.Option(
            help="A path to target class to be evaluated in a format python.path:ModuleName",
            exists=True,
            resolve_path=True,
        ),
    ],
    dataloader_args: Annotated[
        str,
        typer.Option(
            help="Comma separated arguments of dataloader",
            exists=True,
            resolve_path=True,
        ),
    ],
    dataloader_cls: Annotated[
        str | None,
        typer.Option(
            help="Dataloader class path in a format python.path:ModuleName to override the default",
            exists=True,
            resolve_path=True,
        ),
    ] = None,
    target_factory_path: Annotated[
        str | None,
        typer.Option(
            help="A path to a factory of the target class in format: python.path:function_name",
            exists=True,
            resolve_path=True,
        ),
    ] = None,
    target_yaml_path: Annotated[
        Path | None,
        typer.Option(
            help="A path to a YAML configuration file of the target class",
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
    state.evaluation_target = get_instance_or_exit(
        import_by_path(target_cls),
        factory_path=target_factory_path,
        yaml_path=target_yaml_path,
    )
    # TODO validate if given metric set is suitable for evaluation target
    state.metrics = get_instance_or_exit(
        MetricSet, factory_path=metrics_factory_path, yaml_path=metrics_yaml_path, config_override=eval_config
    )
    # TODO validate if given dataloader is suitable for evaluation target
    state.dataloader = get_dataloader_instance(
        config=eval_config, dataloader_args=dataloader_args, dataloader_cls_override=dataloader_cls
    )


@eval_app.command()
def run_evaluation() -> None:
    """
    Evaluate the set-up pipeline.
    """

    async def run() -> None:
        if state.evaluation_target is None:
            raise ValueError("Evaluation target not initialized")
        if state.metrics is None:
            raise ValueError("Evaluation metrics not initialized")
        if state.dataloader is None:
            raise ValueError("Dataloader not initialized")
        evaluation_pipeline = get_evaluation_pipeline_for_target(evaluation_target=state.evaluation_target)
        evaluator = Evaluator()
        metric_results = await evaluator.compute(
            pipeline=evaluation_pipeline,
            metrics=state.metrics,
            dataloader=state.dataloader,
        )
        evaluation_results = EvaluationResult(
            metrics={"metrics": metric_results["metrics"], "time_perf": metric_results["time_perf"]}
        )
        print_output(evaluation_results)

    asyncio.run(run())
