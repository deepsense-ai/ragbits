import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def save(file_path: Path, **data: Any) -> None:
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
