from abc import ABC, abstractmethod
from collections.abc import Callable

from omegaconf import OmegaConf
from ragbits.core.utils.config_handling import WithConstructionConfig


class CallbackConfigurator(WithConstructionConfig, ABC):
    """An abstract class for callback configuration"""

    def __init__(self, config: dict):
        self.config = OmegaConf.create(config)

    @abstractmethod
    def get_callback(self) -> Callable:
        """
        An abstract method for callback configuration
        Args:
            None
        Returns:
            Callable
        """
        pass
