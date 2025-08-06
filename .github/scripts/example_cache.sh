#!/bin/bash

set -euo pipefail

if [ $# -lt 2 ]; then
    echo "Usage: $0 <command> <example_file>"
    echo "Commands:"
    echo "  record <example_file>  - Record successful example run"
    echo "  check <example_file>   - Check if example should be skipped"
    exit 1
fi

COMMAND="$1"
EXAMPLE_FILE="$2"
CACHE_DIR=".example-cache"
BRANCH_REF="${GITHUB_HEAD_REF:-${GITHUB_REF_NAME:-main}}"

# Normalize the branch name for cache key (replace / with -)
CACHE_KEY=$(echo "$BRANCH_REF" | sed 's/\//-/g')
SUCCESS_FILE="$CACHE_DIR/${CACHE_KEY}-$(echo "$EXAMPLE_FILE" | sed 's/\//-/g').success"

mkdir -p "$CACHE_DIR"

case "$COMMAND" in
    "record")
        # Record the current commit hash as successful
        echo "$GITHUB_SHA" > "$SUCCESS_FILE"
        echo "Recorded success for $EXAMPLE_FILE at commit $GITHUB_SHA"
        ;;

    "check")
        # Check if we have a previous success record
        if [ ! -f "$SUCCESS_FILE" ]; then
            echo "false" # No previous success, must run
            exit 0
        fi

        # Get the commit hash from the success file
        LAST_SUCCESS_COMMIT=$(cat "$SUCCESS_FILE")

        # Check if the example file has been modified since the last success
        if git diff --quiet "$LAST_SUCCESS_COMMIT" HEAD -- "$EXAMPLE_FILE"; then
            echo "true" # File unchanged since last success, can skip
        else
            echo "false" # File modified, must run
        fi
        ;;

    *)
        echo "Unknown command: $COMMAND"
        echo "Available commands: record, check"
        exit 1
        ;;
esac
