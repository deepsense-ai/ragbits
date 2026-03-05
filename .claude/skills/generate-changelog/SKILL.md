---
name: generate-changelog
description: Generate changelog entries for packages changed on the current branch.
allowed-tools: Read, Edit
disable-model-invocation: true
---

# Generate Changelog Entries

Generate concise changelog entries for each package with changes on the current branch compared to `main`, and insert them into the package CHANGELOG.md files.

## Current Branch State

Changed files:
!`git fetch origin main 2>/dev/null; git diff --name-only origin/main 2>/dev/null`

Commit messages (check for Changelog-ignore directives):
!`git log --pretty=format:'%B---' origin/main..HEAD 2>/dev/null`

Diff for all packages:
!`git diff origin/main -- packages/ 2>/dev/null`

## Package Detection

From the changed files above, determine which packages need entries:

1. Files matching `packages/<name>/src/**` mean `<name>` is changed — extract the second path component as the package name.
2. If ANY file starts with `typescript/`, treat `ragbits-chat` as a changed package.
3. Ignore files outside `packages/*/src/` and `typescript/` (docs, scripts, CI, etc.).

## Changelog-Ignore

Check the full commit messages for lines matching `Changelog-ignore: <package-name>`. Skip any listed package entirely.

## For Each Package

### 1. Read existing CHANGELOG.md

Read `packages/<package>/CHANGELOG.md`. Look at existing entries to understand the style used in this package.

### 2. Generate entry

Using the commit messages and the package diff above, write a changelog entry following these rules:
- Start with a category prefix: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`, etc.
- Single concise line describing the main user-facing change
- Focus on what changed for users, not internal implementation details
- If there are multiple significant changes, create one entry per distinct change
- Match the style of existing entries in the CHANGELOG

### 3. Insert into CHANGELOG.md

Edit `packages/<package>/CHANGELOG.md` — add entries after `## Unreleased` as bullet points:

```
## Unreleased

- <new entry here>
```

## Summary

After all packages are processed, report:
- Packages with generated entries (and what they are)
- Packages skipped due to Changelog-ignore
- Packages with no meaningful user-facing changes
