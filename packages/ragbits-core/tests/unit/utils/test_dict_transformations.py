from typing import Any

import pytest

from ragbits.core.utils.dict_transformations import SimpleTypes, flatten_dict, unflatten_dict


def test_flatten_dict_simple():
    """Test flattening a simple dictionary."""
    input_dict: dict[str, Any] = {"key1": "value1", "key2": "value2"}
    expected: dict[str, SimpleTypes] = {"key1": "value1", "key2": "value2"}
    assert flatten_dict(input_dict) == expected


def test_flatten_dict_nested():
    """Test flattening a nested dictionary."""
    input_dict = {"key1": "value1", "nested": {"subkey1": "subvalue1", "subkey2": "subvalue2"}}
    expected = {"key1": "value1", "nested.subkey1": "subvalue1", "nested.subkey2": "subvalue2"}
    assert flatten_dict(input_dict) == expected


def test_flatten_dict_deeply_nested():
    """Test flattening a deeply nested dictionary."""
    input_dict = {
        "key1": "value1",
        "nested": {"subkey1": "subvalue1", "deeper": {"deepkey1": "deepvalue1", "deepkey2": "deepvalue2"}},
    }
    expected = {
        "key1": "value1",
        "nested.subkey1": "subvalue1",
        "nested.deeper.deepkey1": "deepvalue1",
        "nested.deeper.deepkey2": "deepvalue2",
    }
    assert flatten_dict(input_dict) == expected


def test_flatten_dict_custom_separator():
    """Test flattening a dictionary with a custom separator."""
    input_dict = {"key1": "value1", "nested": {"subkey1": "subvalue1"}}
    expected = {"key1": "value1", "nested__subkey1": "subvalue1"}
    assert flatten_dict(input_dict, sep="__") == expected


def test_flatten_dict_empty():
    """Test flattening an empty dictionary."""
    assert flatten_dict({}) == {}


def test_flatten_dict_with_non_dict_values():
    """Test flattening a dictionary with various value types."""
    input_dict: dict[str, Any] = {
        "key1": "value1",
        "nested": {"subkey1": 42, "subkey2": [1, 2, 3], "subkey3": {"a": 1}, "subkey4": True, "subkey5": 3.14},
    }
    expected: dict[str, SimpleTypes] = {
        "key1": "value1",
        "nested.subkey1": 42,
        "nested.subkey2[0]": 1,
        "nested.subkey2[1]": 2,
        "nested.subkey2[2]": 3,
        "nested.subkey3.a": 1,
        "nested.subkey4": True,
        "nested.subkey5": 3.14,
    }
    assert flatten_dict(input_dict) == expected


def test_flatten_unflatten():
    """Test flattening and unflattening a dictionary."""
    input_dict: dict[str, Any] = {
        "key1": "value1",
        "nested": {
            "subkey1": "subvalue1",
            "deeper": {
                "deepkey1": 0,
                "deepkey2": "deepvalue2",
                "deepkey3": [1, 2, 3],
                "deepkey4": {"a": 1, "b": 2},
                "deepkey5": True,
                "deepkey6": 3.14,
                "deepkeyevendeeper": [
                    {"a": 1, "b": [1, 2, 3]},
                    {"c": 3, "d": 4},
                ],
            },
        },
    }

    flattened = flatten_dict(input_dict)
    print("Flattened dict:", flattened)
    unflattened = unflatten_dict(flattened)
    print("Unflattened dict:", unflattened)
    assert input_dict == unflattened


def test_simple_flat_dict():
    input_dict = {"a": 1, "b": 2, "c": 3}
    expected = {"a": 1, "b": 2, "c": 3}
    assert unflatten_dict(input_dict) == expected


def test_nested_dot_notation():
    input_dict = {"user.name": "John", "user.age": 30, "user.address.street": "123 Main St"}
    expected = {"user": {"name": "John", "age": 30, "address": {"street": "123 Main St"}}}
    assert unflatten_dict(input_dict) == expected


def test_array_notation():
    input_dict = {"users[0]": "John", "users[1]": "Jane", "users[2]": "Bob"}
    expected = {"users": ["John", "Jane", "Bob"]}
    assert unflatten_dict(input_dict) == expected


def test_mixed_notation():
    input_dict = {"users[0].name": "John", "users[0].age": 30, "users[1].name": "Jane", "users[1].age": 25}
    expected = {"users": [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]}
    assert unflatten_dict(input_dict) == expected


def test_direct_array_indices():
    input_dict = {"0": "First", "1": "Second", "2": "Third"}
    expected = {"0": "First", "1": "Second", "2": "Third"}
    assert unflatten_dict(input_dict) == expected


def test_mixed_types():
    input_dict = {"string": "value", "number": 42, "boolean": True, "nested.value": None}
    expected = {"string": "value", "number": 42, "boolean": True, "nested": {"value": None}}
    assert unflatten_dict(input_dict) == expected


def test_empty_dict():
    input_dict: dict = {}
    expected: dict = {}
    assert unflatten_dict(input_dict) == expected


def test_deep_nesting():
    input_dict = {"a.b.c.d.e": "value", "a.b.c.d.f": "another"}
    expected = {"a": {"b": {"c": {"d": {"e": "value", "f": "another"}}}}}
    assert unflatten_dict(input_dict) == expected


def test_invalid_array_indices():
    input_dict = {"arr[0]": "first", "arr[invalid]": "second"}
    with pytest.raises(ValueError):
        unflatten_dict(input_dict)


def test_mixed_array_and_object():
    input_dict = {"users[0].name": "John", "users[0].pets[0]": "Dog", "users[0].pets[1]": "Cat"}
    expected = {"users": [{"name": "John", "pets": ["Dog", "Cat"]}]}
    assert unflatten_dict(input_dict) == expected


def test_unflatten_dict_notation_based_types():
    """Test that unflatten_dict uses notation to determine types, not heuristics."""
    # Test that numeric keys without array notation stay as dict
    input_dict: dict[str, SimpleTypes] = {"0": "first", "1": "second", "2": "third"}
    expected: dict[str, Any] = {"0": "first", "1": "second", "2": "third"}
    assert unflatten_dict(input_dict) == expected

    # Test that array notation creates lists
    input_dict = {"items[0]": "first", "items[1]": "second", "items[2]": "third"}
    expected = {"items": ["first", "second", "third"]}
    assert unflatten_dict(input_dict) == expected

    # Test mixed notation at different levels
    input_dict = {
        "dict_key": "value",
        "list_key[0]": "first",
        "list_key[1]": "second",
        "nested[0].name": "John",
        "nested[0].age": 30,
        "nested[1].name": "Jane",
        "nested[1].age": 25,
    }
    expected = {
        "dict_key": "value",
        "list_key": ["first", "second"],
        "nested": [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}],
    }
    assert unflatten_dict(input_dict) == expected

    # Test that numeric keys in nested dicts stay as dict
    input_dict = {"config.0.name": "first", "config.1.name": "second", "config.2.name": "third"}
    expected = {"config": {"0": {"name": "first"}, "1": {"name": "second"}, "2": {"name": "third"}}}
    assert unflatten_dict(input_dict) == expected


def test_unflatten_dict_always_returns_dict():
    """Test that unflatten_dict always returns a dict, never a list."""
    # Test with array-like keys
    input_dict = {"0": "first", "1": "second"}
    result = unflatten_dict(input_dict)
    assert isinstance(result, dict)
    assert result == {"0": "first", "1": "second"}

    # Test with array notation
    input_dict = {"items[0]": "first", "items[1]": "second"}
    result = unflatten_dict(input_dict)
    assert isinstance(result, dict)
    assert result == {"items": ["first", "second"]}

    # Test with nested array notation
    input_dict = {"users[0].name": "John", "users[1].name": "Jane"}
    result = unflatten_dict(input_dict)
    assert isinstance(result, dict)
    assert result == {"users": [{"name": "John"}, {"name": "Jane"}]}
