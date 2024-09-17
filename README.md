# Ragbits

Repository for internal experiment with our upcoming LLM framework.


# Setup developer environment

To start, you need to setup your local machine.

## Setup venv

You need to setup virtual environment, simplest way is to run from project root directory:

```bash
$ source ./setup_dev_env.sh
```

This will create a new venv and install all packages from this repository in editable mode.

## Install pre-commit

To ensure code quality we use pre-commit hook with several checks. Setup it by:

```
pre-commit install
```

All updated files will be reformatted and linted before the commit.

To reformat and lint all files in the project, use:

`pre-commit run --all-files`

The used linters are configured in `.pre-commit-config.yaml`. You can use `pre-commit autoupdate` to bump tools to the latest versions.
