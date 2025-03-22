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

# Look for "Changelog-ignore: <package-name>" in the commit message (possibly multiple entries in separate lines)
IGNORED_PACKAGES=$(git log --pretty=format:%B origin/main..HEAD | grep -oP '^Changelog-ignore: \K[^ ]+' | sort -u)

for IGNORED_PACKAGE in $IGNORED_PACKAGES; do
  if echo "$CHANGED_PACKAGES" | grep -q "^$IGNORED_PACKAGE$"; then
    echo "Ignoring changelog check for package: $IGNORED_PACKAGE"
    CHANGED_PACKAGES=$(echo "$CHANGED_PACKAGES" | grep -v "^$IGNORED_PACKAGE$")
  fi
done

for PACKAGE in $CHANGED_PACKAGES; do
  CHANGELOG="packages/$PACKAGE/CHANGELOG.md"
  echo "Checking changelog for package: $PACKAGE"

  if ! diff -u <(git show origin/main:$CHANGELOG | grep -Pzo '(?s)(## Unreleased.*?)(?=\n## |\Z)' | tr -d '\0') <(grep -Pzo '(?s)(## Unreleased.*?)(?=\n## |\Z)' $CHANGELOG | tr -d '\0') | grep -q '^\+'; then
    echo "No updates detected in changelog for package $PACKAGE. Please add an entry under '## Unreleased'."
    exit 1
  fi
done

echo "All modified packages have their changelog updates."
