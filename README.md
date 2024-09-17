# Ragbits

Repository for internal experiment with our upcoming LLM framework.

# Installation

## Build from source

To build and run Ragbits from the source code:

1. Requirements: [**uv**](https://docs.astral.sh/uv/getting-started/installation/) & [**python**](https://docs.astral.sh/uv/guides/install-python/) 3.10 or higher
2. Install dependencies and run venv in editable mode:

```bash
$ source ./setup_dev_env.sh
```

## Install pre-commit

To ensure code quality we use pre-commit hook with several checks. Setup it by:

```
pre-commit install
```

All updated files will be reformatted and linted before the commit.

To reformat and lint all files in the project, use:

`pre-commit run --all-files`

The used linters are configured in `.pre-commit-config.yaml`. You can use `pre-commit autoupdate` to bump tools to the latest versions.
