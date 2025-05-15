import asyncio
import warnings
from collections.abc import Callable
from copy import deepcopy

import optuna
from optuna import Trial
from pydantic import BaseModel

from ragbits.core.utils.config_handling import WithConstructionConfig, import_by_path
from ragbits.evaluate.dataloaders.base import DataLoader
from ragbits.evaluate.evaluator import Evaluator, EvaluatorConfig
from ragbits.evaluate.metrics.base import MetricSet
from ragbits.evaluate.pipelines.base import EvaluationPipeline
from ragbits.evaluate.utils import setup_optuna_neptune_callback


class OptimizerConfig(BaseModel):
    """
    Schema for the optimizer config.
    """

    evaluator: EvaluatorConfig
    optimizer: dict | None = None
    neptune_callback: bool = False


class Optimizer(WithConstructionConfig):
    """
    Optimizer class.
    """

    def __init__(self, direction: str = "maximize", n_trials: int = 10, max_retries_for_trial: int = 1) -> None:
        """
        Initialize the pipeline optimizer.

        Args:
            direction: Direction of optimization.
            n_trials: The number of trials for each process.
            max_retries_for_trial: The number of retires for single process.
        """
        self.direction = direction
        self.n_trials = n_trials
        self.max_retries_for_trial = max_retries_for_trial
        # workaround for optuna not allowing different choices for different trials
        # TODO check how optuna handles parallelism. discuss if we want to have parallel studies
        self._choices_cache: dict[str, list] = {}

    @classmethod
    def run_from_config(cls, config: dict) -> list[tuple[dict, float, dict[str, float]]]:
        """
        Run the optimization process configured with a config object.

        Args:
            config: Optimizer config.

        Returns:
            List of tested configs with associated scores and metrics.
        """
        optimizer_config = OptimizerConfig.model_validate(config)
        evaluator_config = EvaluatorConfig.model_validate(optimizer_config.evaluator)

        dataloader: DataLoader = DataLoader.subclass_from_config(evaluator_config.evaluation.dataloader)
        metricset: MetricSet = MetricSet.from_config(evaluator_config.evaluation.metrics)

        pipeline_class = import_by_path(evaluator_config.evaluation.pipeline.type)
        pipeline_config = dict(evaluator_config.evaluation.pipeline.config)
        callbacks = [setup_optuna_neptune_callback()] if optimizer_config.neptune_callback else []

        optimizer = cls.from_config(optimizer_config.optimizer or {})
        return optimizer.optimize(
            pipeline_class=pipeline_class,
            pipeline_config=pipeline_config,
            metricset=metricset,
            dataloader=dataloader,
            callbacks=callbacks,
        )

    def optimize(
        self,
        pipeline_class: type[EvaluationPipeline],
        pipeline_config: dict,
        dataloader: DataLoader,
        metricset: MetricSet,
        callbacks: list[Callable] | None = None,
    ) -> list[tuple[dict, float, dict[str, float]]]:
        """
        Run the optimization process for given parameters.

        Args:
            pipeline_class: Pipeline to be optimized.
            pipeline_config: Configuration defining the optimization process.
            dataloader: Data loader.
            metricset: Metrics to be optimized.
            callbacks: Experiment callbacks.

        Returns:
            List of tested configs with associated scores and metrics.
        """

        def objective(trial: Trial) -> float:
            return self._objective(
                trial=trial,
                pipeline_class=pipeline_class,
                pipeline_config=pipeline_config,
                dataloader=dataloader,
                metricset=metricset,
            )

        study = optuna.create_study(direction=self.direction)
        study.optimize(
            func=objective,
            n_trials=self.n_trials,
            callbacks=callbacks,
        )
        return sorted(
            [
                (
                    trial.user_attrs["config"],
                    trial.user_attrs["score"],
                    trial.user_attrs["metrics"],
                )
                for trial in study.get_trials()
            ],
            key=lambda x: -x[1] if self.direction == "maximize" else x[1],
        )

    def _objective(
        self,
        trial: Trial,
        pipeline_class: type[EvaluationPipeline],
        pipeline_config: dict,
        dataloader: DataLoader,
        metricset: MetricSet,
    ) -> float:
        """
        Run a single experiment.
        """
        evaluator = Evaluator()
        event_loop = asyncio.get_event_loop()

        score = 1e16 if self.direction == "maximize" else -1e16
        metrics_values = None
        config_for_trial = None

        for attempt in range(1, self.max_retries_for_trial + 1):
            try:
                config_for_trial = deepcopy(pipeline_config)
                self._set_values_for_optimized_params(cfg=config_for_trial, trial=trial, ancestors=[])
                pipeline = pipeline_class.from_config(config_for_trial)

                results = event_loop.run_until_complete(
                    evaluator.compute(
                        pipeline=pipeline,
                        dataloader=dataloader,
                        metricset=metricset,
                    )
                )
                score = sum(results.metrics.values())
                metrics_values = results.metrics
                break
            except Exception as exc:
                message = (
                    f"Execution of the trial failed: {exc}. A retry will be initiated"
                    if attempt < self.max_retries_for_trial
                    else f"Execution of the trial failed: {exc}. Setting the score to {score}"
                )
                warnings.warn(message=message, category=UserWarning)

        trial.set_user_attr("score", score)
        trial.set_user_attr("metrics", metrics_values)
        trial.set_user_attr("config", config_for_trial)

        return score

    def _set_values_for_optimized_params(self, cfg: dict, trial: Trial, ancestors: list[str]) -> None:  # noqa: PLR0912
        """
        Recursive method for sampling parameter values for optuna trial.
        """
        for key, value in cfg.items():
            if isinstance(value, dict):
                if value.get("optimize"):
                    param_id = f"{'.'.join(ancestors)}.{key}"  # type: ignore
                    choices = value.get("choices")
                    values_range = value.get("range")
                    if choices and values_range:
                        raise ValueError("Choices and range cannot be defined in couple")
                    choices_index = self._choices_cache.get(param_id)
                    if choices and not choices_index:
                        choices_index = list(range(len(choices)))
                        self._choices_cache[param_id] = choices_index
                    if values_range:
                        if isinstance(values_range[0], float) and isinstance(values_range[1], float):
                            cfg[key] = trial.suggest_float(name=param_id, low=values_range[0], high=values_range[1])
                        elif isinstance(values_range[0], int) and isinstance(values_range[1], int):
                            cfg[key] = trial.suggest_int(name=param_id, low=values_range[0], high=values_range[1])
                    else:
                        if not choices:
                            raise ValueError("Either choices or range must be specified")
                        choice_idx = trial.suggest_categorical(name=param_id, choices=choices_index)  # type: ignore
                        choice = choices[choice_idx]
                        if isinstance(choice, dict):
                            self._set_values_for_optimized_params(choice, trial, ancestors + [key, str(choice_idx)])  # type: ignore
                        cfg[key] = choice
                else:
                    self._set_values_for_optimized_params(value, trial, ancestors + [key])  # type: ignore
            elif isinstance(value, list):
                for param in value:
                    if isinstance(param, dict):
                        self._set_values_for_optimized_params(param, trial, ancestors + [key])  # type: ignore
