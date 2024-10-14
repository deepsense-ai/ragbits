import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import neptune
from neptune.utils import stringify_unsupported
from omegaconf import DictConfig


def _save(file_path: Path, **data: Any) -> None:
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


def log_to_file(results: dict[str, Any], output_dir: Path) -> None:
    """
    Log the evaluation results locally.

    Args:
        results: The evaluation results.
        output_dir: The output directory.
    """
    metrics_file = output_dir / "metrics.json"
    results_file = output_dir / "results.json"

    _save(metrics_file, metrics=results["metrics"], time_perf=results["time_perf"])
    _save(results_file, results=results["results"])


def log_to_neptune(config: DictConfig, results: dict[str, Any], output_dir: Path) -> None:
    """
    Log the evaluation results to Neptune.

    Args:
        config: The Hydra configuration.
        results: The evaluation results.
        output_dir: The output directory.
    """
    run = neptune.init_run(project=config.neptune.project)
    run["sys/tags"].add(
        [
            config.task.name,
            config.setup.name,
        ]
    )
    run["config"] = stringify_unsupported(config)
    run["evaluation/metrics"] = stringify_unsupported(results["metrics"])
    run["evaluation/time_perf"] = stringify_unsupported(results["time_perf"])
    run["evaluation/metrics.json"].upload((output_dir / "metrics.json").as_posix())
    run["evaluation/results.json"].upload((output_dir / "results.json").as_posix())
