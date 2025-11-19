---
description: Comprehensive release preparation with parallel analysis, examples, and release notes
---

# Release Preparation - Guided Workflow

Follow this systematic approach to prepare a complete release analysis with PR review, example recommendations, and publication-ready release notes.

---

## Phase 1: Determine Base Reference

**Objective**: Identify the comparison baseline for release analysis.

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
- Phase 2: Launch PR analysis agents
- Phase 3: Launch use-case example agents
- Phase 4: Launch release notes agents
- Phase 5: Consolidate and present findings

---

## Phase 2: Launch PR Analysis Agents

**Objective**: Analyze changes comprehensively from multiple angles.

### IMPORTANT: Launch ALL PR analysis agents in PARALLEL
Use a **single message** with **5 Task tool calls** to launch all agents at once:

### Agent Group: PR Analysis

1. **release.pr-analysis**
   - Quantitative analysis of commits and file changes
   - Package impact assessment
   - Change patterns and hot spots

2. **release.pr-theme-and-type-grouper**
   - Categorize commits by type (feat, fix, refactor, etc.)
   - Identify key themes and initiatives
   - Group related changes

3. **release.pr-msg-validator**
   - Validate conventional commit standards
   - Check message quality
   - Identify compliance issues

4. **release.pr-style-validator**
   - Check code quality and style consistency
   - Validate type hints and docstrings
   - Review testing coverage

5. **release.pr-reviewer**
   - Synthesize all PR analysis findings
   - Provide overall assessment
   - Identify critical issues and risks

### Launch Command Structure:
```
Launch the following PR analysis agents in parallel to analyze commits since [base]:
- release.pr-analysis
- release.pr-theme-and-type-grouper
- release.pr-msg-validator
- release.pr-style-validator
- release.pr-reviewer
```

**CRITICAL**: Wait for all agents to complete before proceeding to Phase 3.

---

## Phase 3: Launch Use-Case Example Agents

**Objective**: Generate actionable example recommendations in a pipeline.

### IMPORTANT: Launch in SEQUENCE (pipeline pattern)
These agents form a pipeline where each builds on the previous:

### Agent Group: Use-Case Examples

1. **release.use-case-examples.explorer** (Launch first)
   - Identify new features and capabilities
   - Discover example opportunities
   - Analyze gaps in current examples
   - **Wait for completion**

2. **release.use-case-examples.coder** (Launch second)
   - Design implementation outlines for examples
   - Create code structures and architecture
   - Document learning objectives
   - **Wait for completion**

3. **release.use-case-examples.judge** (Launch third)
   - Evaluate example designs
   - Prioritize for implementation
   - Provide recommendations

### Launch Command Structure:
```
1. First, launch: release.use-case-examples.explorer to analyze features since [base]
2. Then, launch: release.use-case-examples.coder with Explorer's findings
3. Finally, launch: release.use-case-examples.judge to evaluate designs
```

**CRITICAL**: These must run sequentially - each depends on the previous.

---

## Phase 4: Launch Release Notes Agents

**Objective**: Create publication-ready release notes in a pipeline.

### IMPORTANT: Launch in SEQUENCE (pipeline pattern)
These agents form a pipeline for release notes creation:

### Agent Group: Release Notes

1. **release.notes.outliner** (Launch first)
   - Create structured outline from PR analysis
   - Identify narrative and key messages
   - Plan sections and tone
   - **Wait for completion**

2. **release.notes.writer** (Launch second)
   - Write engaging release notes from outline
   - Include code examples
   - Maintain appropriate tone
   - **Wait for completion**

3. **release.notes.reviewer** (Launch third)
   - Review for accuracy and completeness
   - Evaluate clarity and messaging
   - Provide refinement recommendations

### Launch Command Structure:
```
1. First, launch: release.notes.outliner with PR analysis findings
2. Then, launch: release.notes.writer with the outline
3. Finally, launch: release.notes.reviewer to evaluate the draft
```

**CRITICAL**: These must run sequentially - each depends on the previous.

---

## Phase 5: Consolidate and Present Findings

**Objective**: Present comprehensive, actionable release preparation analysis.

### Structure:

#### 📊 PR Analysis Summary
**From release.pr-reviewer (synthesizing all PR agents)**
- Overall release assessment
- Commit and file change statistics
- Key themes and categories
- Code quality evaluation
- Message standards compliance
- Critical issues and risks
- Release readiness assessment

#### 💡 Use-Case Examples Recommendations
**From release.use-case-examples.judge (synthesizing example pipeline)**
- Prioritized example opportunities
- Implementation designs
- Resource requirements
- Expected impact on documentation

#### 📝 Release Notes Package
**From release.notes.reviewer (synthesizing notes pipeline)**
- Publication-ready release notes draft
- Required revisions (if any)
- Quality assessment
- Publication readiness status

#### 🎯 Action Items
Synthesize all findings into prioritized next steps:

1. **Before Release** (critical from PR reviewer):
   - Blocking issues to resolve
   - Breaking change documentation
   - Critical fixes needed

2. **Documentation & Examples** (from examples judge):
   - Priority examples to implement
   - Timeline and resource needs
   - Example quality standards

3. **Release Communication** (from notes reviewer):
   - Release notes revisions needed
   - Publication timeline
   - Communication plan

4. **Process Improvements** (from PR analysis):
   - Standards violations to address
   - Team guidelines to update
   - Tooling/automation opportunities

---

## Important Notes

### Project Context
- **Monorepo**: Multiple packages under `packages/`
- **Commit Standard**: `type(scope): description` (Conventional Commits)
- **Code Style**: ruff (120 char lines), mypy strict, Google-style docstrings
- **Testing**: pytest with async support

### Agent Execution Patterns

**Parallel Execution** (Phase 2 - PR Analysis):
- All 5 PR agents run simultaneously
- No dependencies between them
- Maximum efficiency

**Sequential Pipeline** (Phase 3 & 4 - Examples and Notes):
- Each agent builds on previous output
- Must wait for completion
- Ensures quality through stages

### Best Practices
- ✅ Launch PR agents in parallel (one message, 5 Task calls)
- ✅ Launch pipeline agents sequentially (wait for each)
- ✅ Use TodoWrite to track progress through phases
- ✅ Review PR analysis before launching pipelines
- ✅ Highlight breaking changes prominently
- ✅ Focus on user-facing impacts
- ✅ Provide actionable recommendations

### Common Pitfalls to Avoid
- ❌ Don't launch PR agents sequentially (wastes time)
- ❌ Don't launch pipeline agents in parallel (breaks dependencies)
- ❌ Don't skip consolidation (agents have related findings)
- ❌ Don't ignore critical issues from PR reviewer
- ❌ Don't overlook breaking changes

---

## Agent Organization

### PR Analysis Agents (Parallel)
- `release.pr-analysis` - Quantitative analysis
- `release.pr-theme-and-type-grouper` - Categorization
- `release.pr-msg-validator` - Message standards
- `release.pr-style-validator` - Code quality
- `release.pr-reviewer` - Synthesis

### Use-Case Example Agents (Sequential Pipeline)
- `release.use-case-examples.explorer` → explores features
- `release.use-case-examples.coder` → designs examples
- `release.use-case-examples.judge` → evaluates & prioritizes

### Release Notes Agents (Sequential Pipeline)
- `release.notes.outliner` → creates structure
- `release.notes.writer` → writes content
- `release.notes.reviewer` → reviews quality

---

## Getting Started

**Start with Phase 1**: Identify the base reference, then proceed through phases sequentially.

Each phase builds on the previous one. Use TodoWrite at the start of Phase 1 to create your roadmap.

**Execution Summary**:
1. Phase 1: Manual (determine base)
2. Phase 2: Parallel (5 PR agents at once)
3. Phase 3: Sequential pipeline (3 example agents)
4. Phase 4: Sequential pipeline (3 notes agents)
5. Phase 5: Manual (consolidate and present)
