import importlib.util
import inspect
import os
from pathlib import Path
from typing import Any, get_origin

from ragbits.core.audit.traces import trace
from ragbits.core.config import core_config
from ragbits.core.prompt import Prompt


class PromptDiscovery:
    """
    Discovers Prompt objects within Python modules.

    Args:
        file_pattern (str): The file pattern to search for Prompt objects. Defaults to "**/prompt_*.py"
        root_path (Path): The root path to search for Prompt objects. Defaults to the directory where the script is run.
    """

    def __init__(self, file_pattern: str = core_config.prompt_path_pattern, root_path: Path | None = None):
        self.file_pattern = file_pattern
        self.root_path = root_path or Path.cwd()

    @staticmethod
    def is_prompt_subclass(obj: Any) -> bool:  # noqa: ANN401
        """
        Checks if an object is a class that is a subclass of Prompt (but not Prompt itself).

        Args:
            obj (any): The object to check.

        Returns:
            bool: True if `obj` is a subclass of Prompt, False otherwise.
        """
        # See https://bugs.python.org/issue44293 for the reason why we need to check for get_origin(obj)
        # in order to avoid generic type aliases (which `isclass` sees as classes, but `issubclass` don't).
        return inspect.isclass(obj) and not get_origin(obj) and issubclass(obj, Prompt) and obj != Prompt

    def discover(self) -> set[type[Prompt]]:
        """
        Discovers Prompt objects within the specified file paths.

        Returns:
            set[Prompt]: The discovered Prompt objects.
        """
        with trace(file_patern=self.file_pattern, path=self.root_path) as outputs:
            result_set: set[type[Prompt]] = set()
            for file_path in self.root_path.glob(self.file_pattern):
                # remove file extenson and remove directory separators with dots
                module_name = str(file_path).rsplit(".", 1)[0].replace(os.sep, ".")

                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec is None:
                    print(f"Skipping {file_path}, not a Python module")
                    continue

                module = importlib.util.module_from_spec(spec)

                assert spec.loader is not None  # noqa: S101

                try:
                    spec.loader.exec_module(module)
                except Exception as e:  # pylint: disable=broad-except
                    print(f"Skipping {file_path}, loading failed: {e}")
                    continue

                for _, obj in inspect.getmembers(module):
                    if self.is_prompt_subclass(obj):
                        result_set.add(obj)

                outputs.result_set = result_set

        return result_set
