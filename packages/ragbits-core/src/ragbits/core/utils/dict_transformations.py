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


def unflatten_dict(input_dict: dict[str, Any]) -> dict[str, Any] | list:
    """
    Converts a flattened dictionary with dot notation and array notation into a nested structure.

    This function transforms a dictionary with flattened keys (using dot notation for nested objects
    and bracket notation for arrays) into a nested dictionary or list structure. It handles both
    object-like nesting (using dots) and array-like nesting (using brackets).

    Args:
        input_dict (dict[Any, Any]): A dictionary with flattened keys. Keys can use dot notation
            (e.g., "person.name") or array notation (e.g., "addresses[0].street").

    Returns:
        Union[dict[Any, Any], list]: A nested dictionary or list structure. Returns a list if all
        top-level keys are consecutive integer strings starting from 0.

    Examples:
        >>> unflatten_dict({"person.name": "John", "person.age": 30})
        {'person': {'name': 'John', 'age': 30}}

        >>> unflatten_dict({"addresses[0].street": "Main St", "addresses[1].street": "Broadway"})
        {'addresses': [{'street': 'Main St'}, {'street': 'Broadway'}]}

        >>> unflatten_dict({"0": "first", "1": "second"})
        ['first', 'second']

    Notes:
        - The function recursively processes nested structures
        - If all keys at any level are consecutive integers starting from 0, that level will be
          converted to a list
        - The function preserves the original values for non-nested keys
        - Keys are sorted before processing to ensure consistent results

    Attribution:
        - This function is based on the answer by user "djtubig-malicex" on Stack Overflow: https://stackoverflow.com/a/67905359/27947364
    """
    if not input_dict:
        return {}

    new_dict: dict[Any, Any] = {}
    field_keys = sorted(input_dict.keys())

    def _decompose_key(key: str) -> tuple[str | int | None, str | int | None]:
        _key = str(key)
        _current_key: str | int | None = None
        _current_subkey: str | int | None = None

        for idx, char in enumerate(_key):
            if char == "[":
                _current_key = _key[:idx]
                start_subscript_index = idx + 1
                end_subscript_index = _key.index("]")
                _current_subkey = int(_key[start_subscript_index:end_subscript_index])

                if len(_key[end_subscript_index:]) > 1:
                    _current_subkey = f"{_current_subkey}.{_key[end_subscript_index + 2:]}"
                break
            elif char == ".":
                split_work = _key.split(".", 1)
                if len(split_work) > 1:
                    _current_key, _current_subkey = split_work
                else:
                    _current_key = split_work[0]
                break

        return _current_key, _current_subkey

    for each_key in field_keys:
        field_value = input_dict[each_key]
        current_key, current_subkey = _decompose_key(each_key)

        if current_key is not None and current_subkey is not None:
            if isinstance(current_key, str) and current_key.isdigit():
                current_key = int(current_key)
            if current_key not in new_dict:
                new_dict[current_key] = {}
            new_dict[current_key][current_subkey] = field_value
        else:
            new_dict[each_key] = field_value

    all_digits = True
    highest_digit = -1

    for each_key, each_item in new_dict.items():
        if isinstance(each_item, dict):
            new_dict[each_key] = unflatten_dict(each_item)

        all_digits &= str(each_key).isdigit()
        if all_digits:
            next_digit = int(each_key)
            highest_digit = max(next_digit, highest_digit)

    if all_digits and highest_digit == (len(new_dict) - 1):
        digit_keys = sorted(new_dict.keys(), key=int)
        new_list: list = [None] * (highest_digit + 1)

        for k in digit_keys:
            i = int(k)
            new_list[i] = new_dict[k]

        return new_list

    return new_dict
