---
name: sync-builder-journal
description: Update Builder Journal documentation references after changes to ragbits-example repository. Use when commits in ragbits-example changed and documentation SHA references need updating.
allowed-tools: Read, Edit, Glob, Grep, Bash(curl *), Bash
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
| 1 (class)  | a710e46 | 10:28  | Imports + ChatInterface class  |
| 1 (launch) | a710e46 | 31:33  | `if __name__` block            |
| 2          | 1e350da | 10:32  | Full class with `__init__`     |
| 3          | 7b8504d | 25:36  | `chat()` method with streaming |
| 4          | a9dacad | 29:49  | `chat()` method with history   |
| Complete   | a9dacad | (full) | Entire file                    |

## Current References (Section 2)

| Step             | Commit  | File      | Lines   | Shows                                |
| ---------------- | ------- | --------- | ------- | ------------------------------------ |
| 1 (config)       | 941e5c7 | config.py | (full)  | UICustomization setup                |
| 1 (main)         | 941e5c7 | main.py   | 14:28   | Imports + ui_customization attr      |
| 2                | fcebd10 | main.py   | 17:32   | Persistence import + class attrs     |
| 3 (config top)   | d8efab4 | config.py | 1:10    | New imports + DEFAULT_MODEL          |
| 3 (config form)  | d8efab4 | config.py | 30:41   | UserSettingsForm + user_settings     |
| 3 (main class)   | d8efab4 | main.py   | 23:36   | Updated imports + class attrs + init |
| 3 (main chat)    | d8efab4 | main.py   | 55:63   | Model selection from context         |
| 4                | d276ee3 | main.py   | 60:67   | State tracking                       |
| 5 (config)       | b170986 | config.py | 44:74   | Feedback forms                       |
| 5 (main class)   | b170986 | main.py   | 33:42   | feedback_config + feedback_path      |
| 5 (main method)  | b170986 | main.py   | 78:94   | save_feedback method                 |
| 6 (config)       | d5f7e98 | config.py | 79:97   | get_auth_backend function            |
| 6 (main chat)    | d5f7e98 | main.py   | 54:67   | Greeting on first message            |
| 6 (main block)   | d5f7e98 | main.py   | 102:104 | Auth backend in RagbitsAPI           |
| 7                | b87eb9c | main.py   | 78:87   | Follow-up messages                   |
| 8 (init)         | cb2ff6c | main.py   | 50:52   | uploaded_files dict                  |
| 8 (conversation) | cb2ff6c | main.py   | 79:88   | File context injection               |
| 8 (handler)      | cb2ff6c | main.py   | 121:137 | upload_handler method                |
| Complete (config) | cb2ff6c | config.py | (full) | Entire config file                   |
| Complete (main)  | cb2ff6c | main.py   | (full)  | Entire main file                     |

## Current References (Appendix A)

| Step             | Commit  | File                              | Lines  | Shows                              |
| ---------------- | ------- | --------------------------------- | ------ | ---------------------------------- |
| 1 (Dockerfile)   | dd51c31 | Dockerfile                        | (full) | Container image definition         |
| 1 (dockerignore) | dd51c31 | .dockerignore                     | (full) | Docker ignore rules                |
| 2 (config)       | dd51c31 | infrastructure/config.sh          | (full) | Shared deployment configuration    |
| Deep dive (GCP)  | dd51c31 | infrastructure/gcp/terraform/main.tf | (full) | GCP Terraform resources         |
| Deep dive (AWS)  | dd51c31 | infrastructure/aws/terraform/main.tf | (full) | AWS Terraform resources         |
| Complete         | dd51c31 | infrastructure/*                  | (full) | All deployment files               |
