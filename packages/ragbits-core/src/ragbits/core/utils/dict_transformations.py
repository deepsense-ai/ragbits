from typing import Any

SimpleTypes = str | int | float | bool | None


def flatten_dict(input_dict: dict[str, Any], parent_key: str = "", sep: str = ".") -> dict[str, SimpleTypes]:
    """
    Recursively flatten a nested dictionary and lists, converting non-primitive types to strings.

    Args:
        input_dict: The dictionary to flatten
        parent_key: The parent key for nested keys
        sep: The separator between nested keys

    Returns:
        A flattened dictionary with primitive types and stringified complex types

    Raises:
        ValueError: If the dictionary cannot be safely flattened due to the presence of the separator in the dict key.
    """
    items: dict[str, SimpleTypes] = {}
    for k, v in input_dict.items():
        if sep in k:
            raise ValueError(f"Separator '{sep}' found in key '{parent_key}' Cannot flatten dictionary safely.")

        if "[" in k or "]" in k:
            raise ValueError(f"Key '{k}' cannot consist '[]' characters. Cannot flatten dictionary safely.")

        new_key = f"{parent_key}{sep}{k}" if parent_key else k

        if isinstance(v, dict):
            items = {**items, **flatten_dict(v, new_key, sep=sep)}
        elif isinstance(v, list):
            for i, item in enumerate(v):
                list_key = f"{new_key}[{i}]"
                if isinstance(item, dict):
                    items = {**items, **flatten_dict(item, list_key, sep=sep)}
                else:
                    items[list_key] = item if isinstance(item, SimpleTypes) else str(item)
        else:
            items[new_key] = v if isinstance(v, SimpleTypes) else str(v)

    return items


def unflatten_dict(input_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Converts a flattened dictionary with dot notation and array notation into a nested structure.

    This function transforms a dictionary with flattened keys (using dot notation for nested objects
    and bracket notation for arrays) into a nested dictionary structure. It uses the notation to determine
    whether a value should be a dictionary or list.

    Args:
        input_dict (dict[str, Any]): A dictionary with flattened keys. Keys can use dot notation
            (e.g., "person.name") or array notation (e.g., "addresses[0].street").

    Returns:
        dict[str, Any]: A nested dictionary structure. Lists are created only when using array notation.

    Examples:
        >>> unflatten_dict({"person.name": "John", "person.age": 30})
        {'person': {'name': 'John', 'age': 30}}

        >>> unflatten_dict({"addresses[0].street": "Main St", "addresses[1].street": "Broadway"})
        {'addresses': [{'street': 'Main St'}, {'street': 'Broadway'}]}

        >>> unflatten_dict({"0": "first", "1": "second"})
        {'0': 'first', '1': 'second'}
    """
    if not input_dict:
        return {}

    new_dict: dict[str, Any] = {}

    def _parse_key(key: str) -> list[tuple[str, bool]]:
        """Parse a key into parts, each part being (name, is_array_index)."""
        parts = []
        current = ""
        i = 0
        while i < len(key):
            if key[i] == "[":
                if current:
                    parts.append((current, False))  # Parent is not an array
                    current = ""
                i += 1  # Skip [
                start = i
                while i < len(key) and key[i] != "]":
                    i += 1
                parts.append((key[start:i], True))
                i += 1  # Skip ]
                if i < len(key) and key[i] == ".":
                    i += 1  # Skip .
            elif key[i] == ".":
                if current:
                    parts.append((current, False))
                    current = ""
                i += 1
            else:
                current += key[i]
                i += 1
        if current:
            parts.append((current, False))
        return parts

    def _ensure_array(obj: dict[str, Any], key: str) -> list:
        """Ensure that obj[key] is a list, creating it if necessary."""
        if key not in obj:
            obj[key] = []
        elif not isinstance(obj[key], list):
            obj[key] = []
        return obj[key]

    def _ensure_dict(obj: Any, key: str) -> dict:
        """Ensure that obj[key] is a dict, creating it if necessary."""
        if key not in obj:
            obj[key] = {}
        elif not isinstance(obj[key], dict):
            obj[key] = {}
        return obj[key]

    def _set_value(current: dict[str, Any], parts: list[tuple[str, bool]], value: Any) -> None:
        """Set a value in the dictionary based on the parsed key parts."""
        for i, (part, is_array) in enumerate(parts[:-1]):
            if is_array:
                idx = int(part)
                if i > 0:
                    # Get the parent key and ensure it's an array
                    parent_key = parts[i - 1][0]
                    if isinstance(current, list):
                        while len(current) <= idx:
                            current.append({})
                        current = current[idx]
                    else:
                        current = _ensure_array(current, parent_key)
                        while len(current) <= idx:
                            current.append({})
                        current = current[idx]
            else:
                if i + 1 < len(parts) and parts[i + 1][1]:  # Next part is array
                    if isinstance(current, list):
                        # We're in a list, so we need to ensure the current index has a dict
                        idx = int(parts[i][0])
                        while len(current) <= idx:
                            current.append({})
                        current = current[idx]
                        current = _ensure_array(current, part)
                    else:
                        current = _ensure_array(current, part)
                else:
                    if isinstance(current, list):
                        # We're in a list, so we need to ensure the current index has a dict
                        idx = int(parts[i][0])
                        while len(current) <= idx:
                            current.append({})
                        current = current[idx]
                        current = _ensure_dict(current, part)
                    else:
                        current = _ensure_dict(current, part)

        last_part, is_array = parts[-1]
        if is_array:
            idx = int(last_part)
            if len(parts) == 1:
                # Direct array access like "users[0]"
                parent_key = parts[0][0]
                current = _ensure_array(current, parent_key)
            while len(current) <= idx:
                current.append(None)
            current[idx] = value
        else:
            if isinstance(current, list):
                # We're in a list, so we need to ensure the current index has a dict
                idx = int(parts[-2][0])  # Get the index from the previous part
                while len(current) <= idx:
                    current.append({})
                current = current[idx]
            current[last_part] = value

    # Sort keys to ensure we process parents before children
    field_keys = sorted(input_dict.keys())
    for key in field_keys:
        parts = _parse_key(key)
        if not parts:
            continue

        # Handle the first part specially to ensure it's created in new_dict
        first_part, is_array = parts[0]
        if first_part not in new_dict:
            new_dict[first_part] = {} if not is_array else []

        # Set the value
        if len(parts) == 1:
            if is_array:
                idx = int(first_part)
                current = _ensure_array(new_dict, first_part)
                while len(current) <= idx:
                    current.append(None)
                current[idx] = input_dict[key]
            else:
                new_dict[first_part] = input_dict[key]
        else:
            _set_value(new_dict, parts, input_dict[key])

    return new_dict
