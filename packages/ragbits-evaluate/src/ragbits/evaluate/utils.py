import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from datasets import Dataset
from hydra.core.hydra_config import HydraConfig
from neptune import Run
from neptune.types import File
from neptune.utils import stringify_unsupported
from omegaconf import DictConfig, OmegaConf


def _save(file_path: Path, **data: Any) -> None:  # noqa: ANN401
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

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)


def log_to_file(results: dict, output_dir: Path | None = None) -> Path:
    """
    Log the evaluation results locally.

    Args:
        results: The evaluation results.
        output_dir: The output directory.

    Returns:
        The output directory.
    """
    output_dir = output_dir or Path(HydraConfig.get().runtime.output_dir)
    metrics_file = output_dir / "metrics.json"
    results_file = output_dir / "results.json"

    _save(metrics_file, metrics=results["metrics"], time_perf=results["time_perf"])
    _save(results_file, results=results["results"])

    return output_dir


def log_to_neptune(results: dict, config: DictConfig, tags: str | list[str] | None = None) -> None:
    """
    Log the evaluation results to Neptune.

    Args:
        results: Evaluation results.
        config: Evaluation configuration.
        tags: Experiment tags.
    """
    run = Run(tags=tags)
    run["config"] = stringify_unsupported(config)
    run["evaluation/metrics"] = stringify_unsupported(results["metrics"])
    run["evaluation/time_perf"] = stringify_unsupported(results["time_perf"])
    run["evaluation/results"].upload(File.from_content(json.dumps(results["results"], indent=4), extension="json"))


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
    for idx, (cfg, score, all_metrics) in enumerate(results):
        trial_name = f"trial_{idx}"
        OmegaConf.save(cfg, output_dir / f"{trial_name}.yaml")
        scores[trial_name] = {"score": score, "all_metrics": all_metrics}
    scores_file = output_dir / "scores.json"
    _save(scores_file, scores=scores)
    return output_dir
