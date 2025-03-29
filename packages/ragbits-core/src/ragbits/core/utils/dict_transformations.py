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


def _ensure_array(obj: dict[str, Any] | list[Any], key: str) -> list[Any]:
    """Ensure that obj[key] is a list, creating it if necessary."""
    if isinstance(obj, list):
        return obj
    if key not in obj or not isinstance(obj[key], list):
        obj[key] = []
    return obj[key]


def _ensure_dict(obj: dict[str, Any] | list[Any], key: str) -> dict[str, Any]:
    """Ensure that obj[key] is a dict, creating it if necessary."""
    if isinstance(obj, list):
        # Lists should be handled by the caller
        raise TypeError("Cannot ensure dict in a list")
    if key not in obj or not isinstance(obj[key], dict):
        obj[key] = {}
    return obj[key]


DictOrList = dict[str, Any] | list[Any]


def _handle_array_part(
    current: DictOrList,
    part: str,
    parent_key: str | None = None,
) -> DictOrList:
    """Handle an array part in the key."""
    idx = int(part)
    if isinstance(current, list):
        while len(current) <= idx:
            current.append({})
        return current[idx]
    if parent_key is None:
        raise ValueError(f"Array part '{part}' without parent key")
    current_list = _ensure_array(current, parent_key)
    while len(current_list) <= idx:
        current_list.append({})
    return current_list[idx]


def _handle_dict_part(
    current: DictOrList,
    part: str,
    next_is_array: bool,
    array_idx: int | None = None,
) -> DictOrList:
    """Handle a dictionary part in the key."""
    if isinstance(current, list):
        if array_idx is None:
            raise ValueError("Array index is required when current is a list")
        while len(current) <= array_idx:
            current.append({})
        current = current[array_idx]
        if not isinstance(current, dict):
            current = {}
            current[str(array_idx)] = current
    if next_is_array:
        return _ensure_array(current, part)
    return _ensure_dict(current, part)


def _handle_single_part(
    new_dict: dict[str, Any],
    first_part: str,
    is_array: bool,
    value: SimpleTypes,
) -> None:
    """Handle a single-part key."""
    if is_array:
        idx = int(first_part)
        current = _ensure_array(new_dict, first_part)
        while len(current) <= idx:
            current.append(None)
        current[idx] = value
    else:
        new_dict[first_part] = value


def _handle_last_array_part(
    current_obj: DictOrList,
    last_part: str,
    value: SimpleTypes,
    parts: list[tuple[str, bool]],
) -> None:
    """Handle the last part of the key when it's an array index."""
    idx = int(last_part)
    if len(parts) == 1:
        # Direct array access like "users[0]"
        parent_key = parts[0][0]
        current_obj = _ensure_array(current_obj, parent_key)
    if isinstance(current_obj, list):
        while len(current_obj) <= idx:
            current_obj.append(None)
        current_obj[idx] = value
    else:
        raise TypeError("Expected list but got dict")


def _handle_last_dict_part(
    current_obj: DictOrList,
    last_part: str,
    value: SimpleTypes,
    parts: list[tuple[str, bool]],
) -> None:
    """Handle the last part of the key when it's a dictionary key."""
    if isinstance(current_obj, list):
        # We're in a list, so we need to ensure the current index has a dict
        idx = int(parts[-2][0])  # Get the index from the previous part
        while len(current_obj) <= idx:
            current_obj.append({})
        current_obj = current_obj[idx]
        if not isinstance(current_obj, dict):
            current_obj = {}
            current_obj[str(idx)] = current_obj
    if isinstance(current_obj, dict):
        current_obj[last_part] = value
    else:
        raise TypeError("Expected dict but got list")


def _set_value(current: dict[str, Any], parts: list[tuple[str, bool]], value: SimpleTypes) -> None:
    """Set a value in the dictionary based on the parsed key parts."""
    current_obj: DictOrList = current

    # Handle all parts except the last one
    for i, (part, is_array) in enumerate(parts[:-1]):
        if is_array:
            current_obj = _handle_array_part(current_obj, part, parts[i - 1][0] if i > 0 else None)
        else:
            next_is_array = i + 1 < len(parts) and parts[i + 1][1]
            array_idx = int(parts[i][0]) if isinstance(current_obj, list) else None
            current_obj = _handle_dict_part(current_obj, part, next_is_array, array_idx)

    # Handle the last part
    last_part, is_array = parts[-1]
    if is_array:
        _handle_last_array_part(current_obj, last_part, value, parts)
    else:
        _handle_last_dict_part(current_obj, last_part, value, parts)


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
            _handle_single_part(new_dict, first_part, is_array, input_dict[key])
        else:
            _set_value(new_dict, parts, input_dict[key])

    return new_dict
