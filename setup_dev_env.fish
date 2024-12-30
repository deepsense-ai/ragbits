#!/usr/bin/env fish

if not test -d .venv
    uv venv --python 3.10
    source .venv/bin/activate.fish

    # Install all packages in editable mode
    uv sync
end

source .venv/bin/activate.fish
