---
description: Generate comprehensive changelog with parallel analysis of changes since last stable release
---

# Changelog Generation Command

You are tasked with generating a comprehensive changelog analysis for the Ragbits project.

## Your Task

1. **Identify the base reference**:
   - Check for the last stable minor version release in the CHANGELOG files (e.g., 1.3.0, 1.2.0)
   - If no version is specified, use the "develop" branch as the base
   - Get all commits since that reference

2. **Launch parallel agents** to analyze the changes:
   - **changelog-summarizer**: Summarize all changes and categorize them
   - **example-generator**: Identify new features and suggest examples that could be created
   - **commit-validator**: Validate that commit messages follow conventional commit standards
   - **style-validator**: Check code style and standards consistency across changes
   - **changelog-post-writer**: Write a comprehensive changelog post for release notes

3. **Aggregate results**: Collect outputs from all agents and present a unified summary

## Expected Output Format

Present the results in the following structure:

### 📊 Changelog Summary
(Output from changelog-summarizer agent)

### 💡 Example Ideas
(Output from example-generator agent)

### ✅ Commit Standards Validation
(Output from commit-validator agent)

### 🎨 Style & Standards Check
(Output from style-validator agent)

### 📝 Changelog Post
(Output from changelog-post-writer agent)

## Important Notes

- Use the Task tool to launch agents in **parallel** for efficiency
- Each agent should work independently on the same commit range
- The commit message standard follows: `type(scope): description`
  - Common types: feat, fix, chore, docs, refactor, test, release
  - Scope is optional
- Code follows ruff formatting and linting standards (see pyproject.toml)
- This is a monorepo with multiple packages under `packages/`

## Getting Started

First, determine the base reference (last stable version or branch), then launch all agents in parallel with a single message containing multiple Task tool calls.
