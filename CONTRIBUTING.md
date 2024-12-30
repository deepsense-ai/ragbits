# Installation

## Build from source

To build and run Ragbits from the source code:

1. Requirements: [**uv**](https://docs.astral.sh/uv/getting-started/installation/) & [**python**](https://docs.astral.sh/uv/guides/install-python/) 3.10 or higher
2. Install dependencies and run venv in editable mode:

For bash users:
```bash
$ source ./setup_dev_env.sh
```

For fish users:
```fish
$ source ./setup_dev_env.fish
```

## Linting and formatting
We use `ruff` for linting and formatting our code. To format your code, run:

```bash
$ uvx ruff format
```

To lint the code, run:
```bash
$ uvx ruff check --fix
```

## Type checking
We use `mypy` for type checking. To perform type checking, simply run:

```bash
$ uv run mypy .
```


## Install pre-commit or pre-push hooks

We also recommend to run checkers on pre-commit/push hook. To set it up, follow these steps:

```bash
$ uv run scripts/install_git_hooks.py
```

Then decide whether you want to run the checks before each commit or before each push.
