#!/bin/bash

set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <example_file>"
    exit 1
fi

EXAMPLE_FILE="$1"

echo "Export env variables required for the examples..."
export GOOGLE_CLOUD_PROJECT
export GOOGLE_APPLICATION_CREDENTIALS
export OPENAI_API_KEY
export GEMINI_API_KEY
export ANTHROPIC_API_KEY
export LOGFIRE_TOKEN

GIT_URL_TEMPLATE="git+https://github.com/deepsense-ai/ragbits.git@%s#subdirectory=packages/%s"
PR_BRANCH="${PR_BRANCH:-main}"

has_script_section() {
  local file="$1"
  grep -q "^# /// script" "$file"
}

patch_dependencies() {
  local file="$1"
  local branch="$2"
  local tmp_file
  tmp_file=$(mktemp)
  local in_script_block=false

  while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ "$line" == "# /// script"* ]]; then
      in_script_block=true
      echo "$line" >> "$tmp_file"
      continue
    fi

    if [[ "$line" == "# ///"* && "$in_script_block" == true ]]; then
      in_script_block=false
      echo "$line" >> "$tmp_file"
      continue
    fi

    if [[ "$in_script_block" == true && "$line" == *ragbits* ]]; then
      if [[ "$line" =~ \"([^\"]+)\" ]]; then
        full_pkg="${BASH_REMATCH[1]}"
        pkg_base="${full_pkg%%[*}"
        git_url=$(printf "$GIT_URL_TEMPLATE" "$branch" "$pkg_base")
        echo "# \"${full_pkg} @ ${git_url}\"," >> "$tmp_file"
      else
        echo "$line" >> "$tmp_file"
      fi
    else
      echo "$line" >> "$tmp_file"
    fi

  done < "$file"
  mv "$tmp_file" "$file"
}

if ! has_script_section "$EXAMPLE_FILE"; then
  echo "Skipping $EXAMPLE_FILE (no script section found)"
  exit 0
fi

echo "Running the script: $EXAMPLE_FILE"
patch_dependencies "$EXAMPLE_FILE" "$PR_BRANCH"

set +e
timeout 30s uv run "$EXAMPLE_FILE"
exit_code=$?
set -e

if [[ $exit_code -eq 124 ]]; then
  echo "Script timed out"
  exit 1
elif [[ $exit_code -ne 0 ]]; then
  echo "Script failed"
  exit $exit_code
else
  echo "Script completed successfully."
fi
