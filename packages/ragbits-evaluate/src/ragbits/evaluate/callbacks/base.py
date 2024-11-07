from abc import ABC, abstractmethod
from collections.abc import Callable

from omegaconf import DictConfig


class CallbackConfigurator(ABC):
    """An abstract class for callback configuration"""

    def __init__(self, config: DictConfig):
        self.config = config

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
