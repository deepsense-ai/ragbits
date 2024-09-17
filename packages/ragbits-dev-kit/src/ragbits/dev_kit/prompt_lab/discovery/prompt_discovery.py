import importlib
import inspect
import os
from collections import namedtuple
from typing import Any

from ragbits.core.prompt import Prompt

PromptDetails = namedtuple("PromptDetails", ["system_prompt", "user_prompt", "input_type", "object"])


class PromptDiscovery:
    """
    Discovers Prompt objects within Python modules.

    Args:
        file_paths (list[str]): List of file paths containing Prompt objects.
    """

    def __init__(self, file_paths: list[str]):
        self.file_paths = file_paths

    def is_submodule(self, module: Any, sub_module: Any) -> bool:
        """
        Checks if a module is a submodule of another.

        Args:
            module (module): The parent module.
            sub_module (module): The potential submodule.

        Returns:
            bool: True if `sub_module` is a submodule of `module`, False otherwise.
        """

        try:
            value = module.__spec__.submodule_search_locations[0] in sub_module.__spec__.submodule_search_locations[0]
            return value
        except TypeError:
            return False

    def process_module(self, module: Any, main_module: Any) -> dict:
        """
        Processes a module to find Prompt objects.

        Args:
            module (module): The module to process.
            main_module (module): The main module.

        Returns:
            dict: A dictionary mapping Prompt names to their corresponding PromptDetails objects.
        """
        result_dict = {}

        for key, value in inspect.getmembers(module):
            if inspect.isclass(value) and key != "Prompt" and issubclass(value, Prompt):
                result_dict[key] = value

            elif inspect.ismodule(value) and not key.startswith("_") and self.is_submodule(main_module, value):
                temp_dict = self.process_module(value, main_module)

                if len(temp_dict.keys()) == 0:
                    continue

                result_dict = {**result_dict, **temp_dict}

        return result_dict

    def discover(self) -> dict:
        """
        Discovers Prompt objects within the specified file paths.

        Returns:
            dict: A dictionary mapping Prompt names to their corresponding PromptDetails objects.
        """

        result_dict = {}
        for prompt_path_str in self.file_paths:
            if prompt_path_str.endswith(".py"):
                temp_module = importlib.import_module(os.path.basename(prompt_path_str[:-3]))
            else:
                temp_module = importlib.import_module(os.path.basename(prompt_path_str))

            temp_results = self.process_module(temp_module, temp_module)

            for key, test_obj in temp_results.items():
                if key not in result_dict:
                    result_dict[key] = PromptDetails(
                        system_prompt=test_obj.system_prompt,
                        user_prompt=test_obj.user_prompt,
                        input_type=test_obj.input_type,
                        object=test_obj,
                    )._asdict()

        return result_dict
