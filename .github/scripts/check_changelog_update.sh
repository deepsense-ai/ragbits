#!/bin/bash

echo "Fetching main branch..."
git fetch origin main --depth=1

echo "Identifying changed files between the current branch and main branch..."
CHANGED_FILES=$(git diff --name-only origin/main | tr '\n' ' ')

if [ -z "$CHANGED_FILES" ]; then
  echo "No files have been changed in this branch."
  exit 0
fi

CHANGED_PACKAGES=$(echo "$CHANGED_FILES" | grep -oE 'packages/[^/]+/src' | cut -d '/' -f2 | sort -u)

if [ -z "$CHANGED_PACKAGES" ]; then
  echo "No package changes detected. Skipping changelog check."
  exit 0
fi

echo "Found changes in the following packages: $CHANGED_PACKAGES"

for PACKAGE in $CHANGED_PACKAGES; do
  CHANGELOG="packages/$PACKAGE/CHANGELOG.md"
  echo "Checking changelog for package: $PACKAGE"

  if ! diff -u <(git show origin/main:$CHANGELOG | grep -Pzo '(?s)(## Unreleased.*?)(?=\n## |\Z)' | tr -d '\0') <(grep -Pzo '(?s)(## Unreleased.*?)(?=\n## |\Z)' $CHANGELOG | tr -d '\0') | grep -q '^\+'; then
    echo "No updates detected in changelog for package $PACKAGE. Please add an entry under '## Unreleased'."
    exit 1
  fi
done

echo "All modified packages have their changelog updates."
