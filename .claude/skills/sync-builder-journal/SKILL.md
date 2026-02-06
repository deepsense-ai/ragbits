---
name: sync-builder-journal
description: Update Builder Journal documentation references after changes to ragbits-example repository. Use when commits in ragbits-example changed and documentation SHA references need updating.
allowed-tools: Read, Edit, Glob, Grep, Bash(curl *)
---

# Sync Builder Journal References

Update the Builder Journal documentation after changes to the ragbits-example repository.

## Current state of ragbits-example

- Commits on main: !`curl -s "https://api.github.com/repos/deepsense-ai/ragbits-example/commits?sha=main&per_page=100" | jq -r '.[] | .sha[:7] + " " + (.commit.message | split("\n")[0])'`

## Early Exit Check

**IMPORTANT:** Compare the commits above against the Current References table below. If all SHAs already match — there are no new or changed commits — report "No updates needed" and STOP. Do not proceed further.

## Context

The Builder Journal documentation lives in two repositories:

1. **ragbits** (this repo) - Documentation in `docs/builder-journal/`
2. **ragbits-example** ([deepsense-ai/ragbits-example](https://github.com/deepsense-ai/ragbits-example)) - Companion code

Documentation uses dynamic GitHub references with line ranges:
```
--8<-- "https://raw.githubusercontent.com/deepsense-ai/ragbits-example/<SHA>/src/ragbits_example/main.py:start:end"
```

## Commit Convention

Commits in ragbits-example use format `Section X.Y: Description`:
- X = section number (1, 2, 3...)
- Y = step within section (1, 2, 3, 4...)

## Steps to Execute

1. Compare the HEAD SHA above against the Current References table. If main hasn't moved, stop.

2. For each changed commit, fetch and examine the file with line numbers:
   ```bash
   curl -s 'https://raw.githubusercontent.com/deepsense-ai/ragbits-example/<SHA>/src/ragbits_example/main.py' | cat -n
   ```

3. Read the local documentation files in `docs/builder-journal/` and update references:
   - Update SHA in URL
   - Update line range (`:start:end`) if code structure changed
   - Update `hl_lines` attribute if highlighted lines shifted

4. Update the Current References table in this SKILL.md to match the new state.

5. Commit documentation changes.

## Current References (Section 1)

| Step       | Commit  | Lines  | Shows                          |
| ---------- | ------- | ------ | ------------------------------ |
| 1 (class)  | 944f1dc | 10:28  | Imports + ChatInterface class  |
| 1 (launch) | 944f1dc | 31:33  | `if __name__` block            |
| 2          | b69d2a3 | 10:33  | Full class with `__init__`     |
| 3          | 93b8999 | 26:37  | `chat()` method with streaming |
| 4          | ade4e2b | 30:50  | `chat()` method with history   |
| Complete   | ade4e2b | (full) | Entire file                    |
