#!/bin/bash

set -euo pipefail

find examples -name '*.py' | while read file; do
  echo "Patching dependencies for the script: $file"

  file_dir=$(dirname "$file")
  tmp_file=$(mktemp "$file_dir/tmp_XXXXXX.py")

  cp "$file" "$tmp_file"
  python ./.github/scripts/patch_dependencies.py "$tmp_file" "${PR_BRANCH:-main}"

  echo "Running the script..."
  uv run "$tmp_file"
  rm "$tmp_file"
done

echo "All examples run successfully."
