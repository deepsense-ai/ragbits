---
description: Generate comprehensive changelog with parallel analysis of changes since last stable release
---

# Changelog Generation - Guided Workflow

Follow this systematic approach to generate comprehensive changelog analysis for release preparation.

---

## Phase 1: Determine Base Reference

**Objective**: Identify the comparison baseline for changelog generation.

### Steps:
1. Check CHANGELOG.md files in `packages/*/CHANGELOG.md` for the last stable version (e.g., 1.3.0, 1.2.0)
2. Look for the most recent version number that's not "Unreleased"
3. If no clear version found, ask the user which base to use (e.g., "develop" branch, specific tag, or commit)
4. Report the base reference and commit count to analyze

### Output:
```
📍 Base Reference: [version/branch]
📊 Commits to analyze: [count]
📅 Date range: [from] to [now]
```

**Use TodoWrite**: Create a todo list for the phases:
- Phase 1: Determine base reference ✓
- Phase 2: Launch parallel analysis agents
- Phase 3: Review and consolidate findings
- Phase 4: Generate final output

---

## Phase 2: Launch Parallel Analysis Agents

**Objective**: Analyze changes from multiple perspectives simultaneously.

### IMPORTANT: Launch ALL agents in PARALLEL
Use a **single message** with **5 Task tool calls** to launch all agents at once:

1. **changelog-summarizer**
   - Categorize commits by type (feat, fix, refactor, etc.)
   - Group changes by package
   - Identify key themes and impact

2. **example-generator**
   - Identify new features
   - Suggest practical examples
   - Propose tutorial ideas

3. **commit-validator**
   - Validate conventional commit format
   - Check message quality
   - Identify compliance issues

4. **style-validator**
   - Check code style consistency
   - Validate type hints and docstrings
   - Review testing standards

5. **changelog-post-writer**
   - Write user-friendly release notes
   - Create migration guides for breaking changes
   - Generate social media blurbs

### Launch Command Structure:
```
Launch the following agents in parallel to analyze commits since [base]:
- changelog-summarizer
- example-generator
- commit-validator
- style-validator
- changelog-post-writer
```

**CRITICAL**: Wait for all agents to complete before proceeding to Phase 3.

---

## Phase 3: Review and Consolidate Findings

**Objective**: Aggregate agent outputs and identify key insights.

### Steps:
1. Review each agent's output carefully
2. Identify common themes across agents
3. Note any conflicts or inconsistencies
4. Highlight critical issues (breaking changes, standards violations)
5. Prepare cross-references between agent findings

### Consolidation Checklist:
- [ ] All 5 agents completed successfully
- [ ] Breaking changes identified and documented
- [ ] Commit/style issues categorized by severity
- [ ] New features mapped to example ideas
- [ ] Key themes and highlights extracted

---

## Phase 4: Generate Final Output

**Objective**: Present comprehensive, actionable changelog analysis.

### Structure:

#### 📊 Changelog Summary
**From changelog-summarizer agent**
- Total commits and file changes
- Changes by category (feat, fix, refactor, etc.)
- Changes by package
- Key themes and highlights
- Impact assessment

#### 💡 Example Ideas
**From example-generator agent**
- New features requiring examples
- Suggested example implementations
- Tutorial and documentation ideas
- Improvements to existing examples

#### ✅ Commit Standards Validation
**From commit-validator agent**
- Compliance statistics
- Issues found (critical, warnings, info)
- Common problems and patterns
- Recommendations for improvement
- Exemplary commits

#### 🎨 Style & Standards Check
**From style-validator agent**
- Overall quality assessment
- Type hint and documentation coverage
- Style inconsistencies
- Testing gaps
- Recommendations

#### 📝 Release Notes Draft
**From changelog-post-writer agent**
- Complete release announcement
- Breaking changes with migration guides
- Feature highlights with examples
- Social media blurbs
- Resources and links

#### 🎯 Action Items
Synthesize findings into actionable next steps:
1. **Before Release** (critical):
   - List any blocking issues
2. **Documentation Needed**:
   - Examples to create
   - Migration guides to write
3. **Process Improvements**:
   - Standards violations to address
   - Team guidelines to update

---

## Important Notes

### Project Context
- **Monorepo**: Multiple packages under `packages/`
- **Commit Standard**: `type(scope): description` (Conventional Commits)
- **Code Style**: ruff (120 char lines), mypy strict, Google-style docstrings
- **Testing**: pytest with async support

### Best Practices
- ✅ Launch agents in parallel (one message, multiple Task calls)
- ✅ Use TodoWrite to track progress through phases
- ✅ Wait for all agents before consolidating
- ✅ Highlight breaking changes prominently
- ✅ Focus on user-facing impacts
- ✅ Provide actionable recommendations

### Common Pitfalls to Avoid
- ❌ Don't launch agents sequentially (wastes time)
- ❌ Don't skip consolidation (agents may have related findings)
- ❌ Don't ignore commit/style violations (affects release quality)
- ❌ Don't overlook breaking changes (critical for users)

---

## Getting Started

**Start with Phase 1**: Identify the base reference, then proceed through phases sequentially.

Each phase builds on the previous one. Use TodoWrite at the start of Phase 1 to create your roadmap.
