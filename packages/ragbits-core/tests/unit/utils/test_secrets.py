import os
from unittest.mock import patch

import pytest

from ragbits.core.utils.secrets import RAGBITS_KEY_ENV_VAR, get_secret_key


def test_get_secret_key_from_env():
    """Test getting the secret key from an environment variable."""
    get_secret_key.cache_clear()
    test_key = "test-env-secret-key"
    with patch.dict(os.environ, {RAGBITS_KEY_ENV_VAR: test_key}, clear=True):
        assert get_secret_key() == test_key


def test_get_secret_key_generates_random():
    """Test that a random key is generated when neither env var nor default is provided."""
    with patch.dict(os.environ, {}, clear=True):
        # The function is cached, so we need to test with different env_var names
        key1 = get_secret_key(env_var="TEST_KEY_1")
        key2 = get_secret_key(env_var="TEST_KEY_2")

        # Keys should be different and not empty
        assert key1 != key2
        assert key1
        assert key2


def test_get_secret_key_warning():
    """Test that a warning is emitted when generating a random key."""
    with (
        patch.dict(os.environ, {}, clear=True),
        pytest.warns(UserWarning, match=f"No secret key found in environment variable {RAGBITS_KEY_ENV_VAR}"),
    ):
        get_secret_key(env_var=RAGBITS_KEY_ENV_VAR)


def test_get_secret_key_caching():
    """Test that the secret key function caches results."""
    with patch.dict(os.environ, {}, clear=True):
        # The same env_var should produce the same key due to caching
        key1 = get_secret_key(env_var="TEST_CACHE_KEY")
        key2 = get_secret_key(env_var="TEST_CACHE_KEY")
        assert key1 == key2
