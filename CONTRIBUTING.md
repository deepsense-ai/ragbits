# Installation

## Build from source

Dependencies needed to build and run Ragbits from the source code:

1. [**uv**](https://docs.astral.sh/uv/getting-started/installation/)
2. [**python**](https://docs.astral.sh/uv/guides/install-python/) 3.10


## Linting and formatting
We use `ruff` for linting and formatting our code. To format your code, run:

```bash
$ uv run ruff format
```

To lint the code, run:
```bash
$ uv run ruff check --fix
```

## Type checking
We use `mypy` for type checking. To perform type checking, simply run:

```bash
$ uv run mypy .
```

## Testing
We use `pytest` for testing. To run the tests, simply run:

```bash
$ uv run pytest
```


## Install pre-commit or pre-push hooks

We also recommend to run checkers on pre-commit/push hook. To set it up, follow these steps:

```bash
$ uv run scripts/install_git_hooks.py
```

Then decide whether you want to run the checks before each commit or before each push.
