#!/bin/bash

set -euo pipefail

# Export variables required for the examples
export GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT}"
export GOOGLE_APPLICATION_CREDENTIALS="${GOOGLE_APPLICATION_CREDENTIALS}"
export OPENAI_API_KEY="${OPENAI_API_KEY}"
export GEMINI_API_KEY="${GEMINI_API_KEY}"
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}"
export LOGFIRE_TOKEN="${LOGFIRE_TOKEN}"

echo "GOOGLE_APPLICATION_CREDENTIALS: $GOOGLE_APPLICATION_CREDENTIALS"
echo "OPENAI_API_KEY: ${OPENAI_API_KEY:0:5}"

find examples -name '*.py' | while read file; do
  echo "Running the script: $file"

  # Copying the file to a temporary location
  file_dir=$(dirname "$file")
  tmp_file=$(mktemp "$file_dir/tmp_XXXXXX.py")
  cp "$file" "$tmp_file"

  # Patching the dependencies based on the PR branch
  python ./.github/scripts/patch_dependencies.py "$tmp_file" "${PR_BRANCH:-main}"

  # Running the script with uv
  uv run "$tmp_file"
  rm "$tmp_file"
done

echo "All examples run successfully."
