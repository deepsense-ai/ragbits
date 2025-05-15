import json
import sys
import traceback
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from datasets import Dataset
from hydra.core.hydra_config import HydraConfig
from neptune import Run
from neptune.types import File
from neptune.utils import stringify_unsupported
from neptune_optuna import NeptuneCallback
from omegaconf import DictConfig

from ragbits.evaluate.evaluator import EvaluatorResult


def log_evaluation_to_file(result: EvaluatorResult, output_dir: Path | None = None) -> Path:
    """
    Log the evaluation result locally.

    Args:
        result: The evaluation result.
        output_dir: The output directory.

    Returns:
        The output directory.
    """
    output_dir = output_dir or Path(HydraConfig.get().runtime.output_dir)
    metrics_file = output_dir / "metrics.json"
    results_file = output_dir / "results.json"
    errors_file = output_dir / "errors.json"

    _save_json(metrics_file, metrics=result.metrics, time_perf=asdict(result.time_perf))
    _save_json(results_file, results=[asdict(entry) for entry in result.results])
    _save_json(
        errors_file,
        errors=[
            {
                "type": exc.__class__.__name__,
                "message": str(exc),
                "stacktrace": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
            }
            for exc in result.errors
        ],
    )

    return output_dir


def log_evaluation_to_neptune(result: EvaluatorResult, config: DictConfig, tags: str | list[str] | None = None) -> None:
    """
    Log the evaluation result to Neptune.

    Args:
        result: The evaluation result.
        config: The evaluation configuration.
        tags: The experiment tags.
    """
    run = Run(tags=tags)
    run["config"] = stringify_unsupported(config)
    run["evaluation/metrics"] = stringify_unsupported(result.metrics)
    run["evaluation/time_perf"] = stringify_unsupported(asdict(result.time_perf))
    run["evaluation/results"].upload(
        File.from_content(json.dumps([asdict(entry) for entry in result.results], indent=4), extension="json")
    )
    run["evaluation/errors"].upload(
        File.from_content(
            json.dumps(
                [
                    {
                        "type": exc.__class__.__name__,
                        "message": str(exc),
                        "stacktrace": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
                    }
                    for exc in result.errors
                ],
                indent=4,
            ),
            extension="json",
        )
    )


def log_dataset_to_file(dataset: Dataset, output_dir: Path | None = None) -> Path:
    """
    Log the evaluation results locally.

    Args:
        dataset: Huggingface dataset to be logged.
        output_dir: The output directory.

    Returns:
        The output directory.
    """
    output_dir = output_dir or Path(HydraConfig.get().runtime.output_dir)
    dataset_file = output_dir / "dataset.hf"
    dataset.save_to_disk(dataset_path=str(dataset_file))
    return output_dir


def log_optimization_to_file(
    results: list[tuple[dict, float, dict[str, float]]], output_dir: Path | None = None
) -> Path:
    """
    Log the evaluation results locally.

    Args:
        results: The evaluation results.
        output_dir: The output directory.

    Returns:
        The output directory.
    """
    output_dir = output_dir or Path(HydraConfig.get().runtime.output_dir)

    scores = {}
    for i, (config, score, all_metrics) in enumerate(results):
        trial_name = f"trial-{i}"
        scores[trial_name] = {"score": score, "all_metrics": all_metrics}
        trial_config_file = output_dir / f"{trial_name}.json"
        _save_json(trial_config_file, config=config)

    scores_file = output_dir / "scores.json"
    _save_json(scores_file, scores=scores)

    return output_dir


def _save_json(file_path: Path, **data: Any) -> None:  # noqa: ANN401
    """
    Save the data to a file. Add the current timestamp and Python version to the data.

    Args:
        file_path: The path to the file.
        data: The data to be saved.
    """
    current_time = datetime.now()

    data["_timestamp"] = current_time.isoformat()
    data["_python_version"] = sys.version
    data["_interpreter_path"] = sys.executable

    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)


def setup_optuna_neptune_callback(tags: str | list[str] | None = None) -> NeptuneCallback:
    """
    Log the optimization process to Neptune.

    Args:
        tags: Experiment tags.
    """
    run = Run(tags=tags)
    return NeptuneCallback(run)
