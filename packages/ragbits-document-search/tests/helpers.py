import os


def env_vars_not_set(env_vars: list[str]) -> bool:
    return all(os.environ.get(env_var) is None for env_var in env_vars)
