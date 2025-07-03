#!/bin/bash

# Get the changed files between the specified commits
CHANGED_FILES=$(git diff --name-only "$1" "$2")

# Check if any non-UI files have changed
PACKAGES_CHANGED=$(echo "$CHANGED_FILES" | grep -qv '^typescript/ui/' && echo "true" || echo "false")

# Check if any UI files have changed
UI_CHANGED=$(echo "$CHANGED_FILES" | grep -q '^typescript/ui/' && echo "true" || echo "false")

# Check if any TypeScript module files have changed (@ragbits/api-client or @ragbits/api-client-react)
CLIENT_CHANGED=$(echo "$CHANGED_FILES" | grep -q '^typescript/@ragbits/api-client' && echo "true" || echo "false")

# Set the GitHub outputs
echo "packages-changed=$PACKAGES_CHANGED" >> "$GITHUB_OUTPUT"
echo "ui-changed=$UI_CHANGED" >> "$GITHUB_OUTPUT"
echo "client-changed=$CLIENT_CHANGED" >> "$GITHUB_OUTPUT"
