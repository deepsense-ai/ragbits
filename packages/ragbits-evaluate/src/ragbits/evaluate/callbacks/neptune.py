import sys
from collections.abc import Callable

import neptune

from ragbits.core.utils.config_handling import get_cls_from_config

from .base import CallbackConfigurator

module = sys.modules[__name__]


class NeptuneCallbackConfigurator(CallbackConfigurator):
    """A class for configuration of neptune callbacks"""

    def get_callback(self) -> Callable:
        """
        Creates neptune callback based on configuration
        Args:
            None
        Returns:
            Callable: configured neptune callback
        """
        callback_class = get_cls_from_config(self.config.callback_type, module)
        run = neptune.init_run(project=self.config.project)
        return callback_class(run)
