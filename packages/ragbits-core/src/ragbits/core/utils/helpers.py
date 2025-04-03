import os


def env_vars_not_set(env_vars: list[str]) -> bool:
    """
    Checks if no environment variable is set.

    Args:
        env_vars: The list of environment variables to check.

    Returns:
        True if no environment variable is set, otherwise False.
    """
    return all(os.environ.get(env_var) is None for env_var in env_vars)
