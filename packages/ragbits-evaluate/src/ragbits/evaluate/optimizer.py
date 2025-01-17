import asyncio
import sys
import warnings
from copy import deepcopy
from typing import Any, cast

import optuna
from omegaconf import DictConfig, ListConfig, OmegaConf

from ragbits.core.utils.config_handling import WithConstructionConfig, import_by_path

from .callbacks.base import CallbackConfigurator
from .evaluator import Evaluator
from .loaders import dataloader_factory
from .loaders.base import DataLoader
from .metrics import metric_set_factory
from .metrics.base import MetricSet
from .pipelines.base import EvaluationPipeline

module = sys.modules[__name__]


class Optimizer(WithConstructionConfig):
    """
    Optimizer class.
    """

    INFINITY = 1e16

    def __init__(self, config: dict):
        self.config = OmegaConf.create(config)
        # workaround for optuna not allowing different choices for different trials
        # TODO check how optuna handles parallelism. discuss if we want to have parallel studies
        self._choices_cache: dict[str, list[Any]] = {}

    @classmethod
    def run_from_config(cls, config: dict) -> list[tuple[dict, float, dict[str, float]]]:
        """
        Runs the optimization process configured with a config object.

        Args:
            config: Optimizer config.

        Returns:
            List of tested configs with associated scores.
        """
        optimizer_config = OmegaConf.create(config["optimizer"])
        exp_config = OmegaConf.create(config["experiment"])
        dataloader = dataloader_factory(cast(dict, OmegaConf.to_container(exp_config.dataloader)))
        pipeline_class = import_by_path(exp_config.pipeline.type, module)
        metrics = metric_set_factory(exp_config.metrics.values())
        callback_configurators = None
        if getattr(exp_config, "callbacks", None):
            callback_configurators = [
                import_by_path(callback_cfg.type, module)(OmegaConf.to_container(callback_cfg.args))
                for callback_cfg in exp_config.callbacks
            ]

        optimizer_config_dict = {"config": OmegaConf.to_container(optimizer_config)}
        optimizer = cls.from_config(optimizer_config_dict)
        return optimizer.optimize(
            pipeline_class=pipeline_class,
            config_with_params=exp_config.pipeline,
            metrics=metrics,
            dataloader=dataloader,
            callback_configurators=callback_configurators,
        )

    def optimize(
        self,
        pipeline_class: type[EvaluationPipeline],
        config_with_params: DictConfig,
        dataloader: DataLoader,
        metrics: MetricSet,
        callback_configurators: list[CallbackConfigurator] | None = None,
    ) -> list[tuple[dict, float, dict[str, float]]]:
        """
        Runs the optimization process for given parameters.

        Args:
            pipeline_class: Pipeline to be optimized.
            config_with_params: Configuration defining the optimization process.
            dataloader: Data loader.
            metrics: Metrics to be optimized.
            callback_configurators: Experiment callback configurator.

        Returns:
            List of tuples with configs and their scores.
        """
        # TODO check details on how to parametrize optuna
        optimization_kwargs = {"n_trials": self.config.n_trials}
        if callback_configurators:
            optimization_kwargs["callbacks"] = [configurator.get_callback() for configurator in callback_configurators]

        def objective(trial: optuna.Trial) -> float:
            return self._objective(
                trial=trial,
                pipeline_class=pipeline_class,
                config_with_params=config_with_params,
                dataloader=dataloader,
                metrics=metrics,
            )

        study = optuna.create_study(direction=self.config.direction)

        study.optimize(objective, **optimization_kwargs)
        configs_with_scores = [
            (
                cast(dict, OmegaConf.to_container(trial.user_attrs["cfg"])),
                trial.user_attrs["score"],
                trial.user_attrs["all_metrics"],
            )
            for trial in study.get_trials()
        ]

        def sorting_key(results: tuple[dict, float, dict[str, float]]) -> float:
            if self.config.direction == "maximize":
                return -results[1]
            else:
                return results[1]

        return sorted(configs_with_scores, key=sorting_key)

    def _objective(
        self,
        pipeline_class: type[EvaluationPipeline],
        trial: optuna.Trial,
        config_with_params: DictConfig,
        dataloader: DataLoader,
        metrics: MetricSet,
    ) -> float:
        max_retries = getattr(self.config, "max_retries_for_trial", 1)
        config_for_trial = None
        for attempt_idx in range(max_retries):
            try:
                config_for_trial = deepcopy(config_with_params)
                self._set_values_for_optimized_params(cfg=config_for_trial, trial=trial, ancestors=[])
                pipeline = pipeline_class.from_config({"config": OmegaConf.to_container(config_for_trial)})
                metrics_values = self._score(pipeline=pipeline, dataloader=dataloader, metrics=metrics)
                score = sum(metrics_values.values())
                break
            except Exception as e:
                if attempt_idx < max_retries - 1:
                    warnings.warn(
                        message=f"Execution of the trial failed: {e}. A retry will be initiated.", category=UserWarning
                    )
                else:
                    score = self.INFINITY
                    if self.config.direction == "maximize":
                        score *= -1
                    metrics_values = {}
                    warnings.warn(
                        message=f"Execution of the trial failed: {e}. Setting the score to {score}",
                        category=UserWarning,
                    )
        trial.set_user_attr("score", score)
        trial.set_user_attr("cfg", config_for_trial)
        trial.set_user_attr("all_metrics", metrics_values)
        return score

    @staticmethod
    def _score(pipeline: EvaluationPipeline, dataloader: DataLoader, metrics: MetricSet) -> dict[str, float]:
        evaluator = Evaluator()
        event_loop = asyncio.get_event_loop()
        results = event_loop.run_until_complete(
            evaluator.compute(pipeline=pipeline, dataloader=dataloader, metrics=metrics)
        )
        return results["metrics"]

    def _set_values_for_optimized_params(self, cfg: DictConfig, trial: optuna.Trial, ancestors: list[str]) -> None:  # noqa: PLR0912
        """
        Recursive method for sampling parameter values for optuna trial.
        """
        for key, value in cfg.items():
            if isinstance(value, DictConfig):
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
                        if isinstance(choice, DictConfig):
                            self._set_values_for_optimized_params(choice, trial, ancestors + [key, str(choice_idx)])  # type: ignore
                        cfg[key] = choice
                else:
                    self._set_values_for_optimized_params(value, trial, ancestors + [key])  # type: ignore
            elif isinstance(value, ListConfig):
                for param in value:
                    if isinstance(param, DictConfig):
                        self._set_values_for_optimized_params(param, trial, ancestors + [key])  # type: ignore
