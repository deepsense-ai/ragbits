from abc import ABC, abstractmethod
from collections.abc import Callable

from omegaconf import OmegaConf

from ragbits.core.utils.config_handling import WithConstructionConfig


class CallbackConfigurator(WithConstructionConfig, ABC):
    """
    Ccallback configurator base class.
    """

    def __init__(self, config: dict):
        self.config = OmegaConf.create(config)

    @abstractmethod
    def get_callback(self) -> Callable:
        """
        Returns configured callback.

        Returns:
            Configured callback.
        """
