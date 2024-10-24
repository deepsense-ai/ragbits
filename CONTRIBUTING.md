# Installation

## Build from source

To build and run Ragbits from the source code:

1. Requirements: [**uv**](https://docs.astral.sh/uv/getting-started/installation/) & [**python**](https://docs.astral.sh/uv/guides/install-python/) 3.10 or higher
2. Install dependencies and run venv in editable mode:

```bash
$ source ./setup_dev_env.sh
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


## Install pre-commit

We also run some checks through a pre-commit hook. To set it up, follow these steps:

```
pre-commit install
```

All updated files will be reformatted and linted before the commit.

To reformat and lint all files in the project, use:

`pre-commit run --all-files`

The used linters are configured in `.pre-commit-config.yaml`. You can use `pre-commit autoupdate` to bump tools to the latest versions.
