# Claude Code Configuration

This directory contains custom commands and agents for Claude Code to help with comprehensive release preparation.

## Command

### `/release.prepare`

Comprehensive release preparation workflow with parallel PR analysis, sequential example generation, and release notes creation.

**Usage**:
```
/release.prepare
```

**What it does** (5 phases):

**Phase 1: Determine Base Reference**
- Identifies the last stable version from CHANGELOG.md files
- Reports commit count and date range to analyze

**Phase 2: PR Analysis (Parallel)**
- Launches 5 specialized agents **simultaneously**:
  - `release.pr-analysis`: Quantitative commit and file analysis
  - `release.pr-theme-and-type-grouper`: Categorization and theme identification
  - `release.pr-msg-validator`: Commit message standards validation
  - `release.pr-style-validator`: Code quality and style checks
  - `release.pr-reviewer`: Synthesis of all PR findings

**Phase 3: Use-Case Examples (Sequential Pipeline)**
- Launches 3 agents in **sequence** (each builds on previous):
  - `release.use-case-examples.explorer`: Discovers example opportunities
  - `release.use-case-examples.coder`: Designs implementation outlines
  - `release.use-case-examples.judge`: Evaluates and prioritizes examples

**Phase 4: Release Notes (Sequential Pipeline)**
- Launches 3 agents in **sequence** (each builds on previous):
  - `release.notes.outliner`: Creates structured outline
  - `release.notes.writer`: Writes engaging release notes
  - `release.notes.reviewer`: Reviews for quality and accuracy

**Phase 5: Consolidate and Present**
- Comprehensive PR analysis summary
- Prioritized example recommendations
- Publication-ready release notes
- Action items by priority

**Output**: Complete release preparation package with analysis, examples plan, and release notes

---

## Agents

### PR Analysis Agents (Parallel Execution)

#### `release.pr-analysis`

Quantitative analysis of commits and file changes.

**Output**: Statistics, file impact, package breakdown, hot spots, change patterns

#### `release.pr-theme-and-type-grouper`

Categorizes commits and identifies themes.

**Output**: Type distribution, changes by category, key themes, breaking changes, cross-package initiatives

#### `release.pr-msg-validator`

Validates commit message standards.

**Output**: Compliance report, violations by severity, common issues, recommendations, exemplary commits

#### `release.pr-style-validator`

Validates code quality and style.

**Output**: Quality assessment, type hint coverage, documentation quality, testing gaps, recommendations

#### `release.pr-reviewer`

Synthesizes all PR analysis findings.

**Output**: Comprehensive review, quality scores, critical findings, risk assessment, release readiness

---

### Use-Case Example Agents (Sequential Pipeline)

#### `release.use-case-examples.explorer`

Explores new features and identifies example opportunities.

**Output**: Feature analysis, example opportunities, gap analysis, priority ranking

#### `release.use-case-examples.coder`

Designs implementation outlines for examples.

**Input**: Explorer's opportunity list
**Output**: Detailed implementation designs, code outlines, learning objectives, architecture plans

#### `release.use-case-examples.judge`

Evaluates and prioritizes example designs.

**Input**: Coder's implementation designs
**Output**: Quality evaluations, prioritized recommendations, implementation timeline, resource estimates

---

### Release Notes Agents (Sequential Pipeline)

#### `release.notes.outliner`

Creates structured outline for release notes.

**Input**: PR analysis findings
**Output**: Narrative structure, section plan, tone guidance, content priorities

#### `release.notes.writer`

Writes engaging, comprehensive release notes.

**Input**: Outliner's structure
**Output**: Complete release notes draft with examples, migration guides, highlights

#### `release.notes.reviewer`

Reviews release notes for quality and readiness.

**Input**: Writer's draft
**Output**: Quality assessment, required revisions, publication readiness evaluation

---

## Agent Organization

### 🔀 Parallel Execution (Phase 2)
```
release.pr-analysis ─────────┐
release.pr-theme-and-type-grouper ─┐
release.pr-msg-validator ──────┼──→ release.pr-reviewer
release.pr-style-validator ─────┘
```
All PR agents run simultaneously for maximum efficiency.

### 🔗 Sequential Pipelines (Phases 3 & 4)
```
Examples Pipeline:
explorer → coder → judge

Release Notes Pipeline:
outliner → writer → reviewer
```
Each agent in the pipeline builds on the previous agent's output.

---

## Project Standards

This project follows:

- **Commit Messages**: Conventional Commits format (`type(scope): description`)
- **Code Style**: ruff (120 char lines, PEP 8 based)
- **Type Checking**: mypy with strict mode for `ragbits.*`
- **Testing**: pytest with async support
- **Docstrings**: Google style convention

---

## Examples

### Complete Release Preparation

To prepare for a release with comprehensive analysis:

```
/release.prepare
```

The command follows a structured 5-phase workflow:
1. **Phase 1**: Determines base reference (last stable version like 1.3.0)
2. **Phase 2**: Launches 5 PR analysis agents in parallel
3. **Phase 3**: Runs example pipeline (explorer → coder → judge)
4. **Phase 4**: Runs release notes pipeline (outliner → writer → reviewer)
5. **Phase 5**: Presents consolidated findings with action items

**Total agents**: 11 specialized agents working together

---

## Tips

- The `/release.prepare` command follows a **mixed execution pattern**
- **Phase 2** runs 5 agents in **parallel** for PR analysis speed
- **Phases 3 & 4** run pipelines **sequentially** for quality progression
- Each agent provides a unique perspective or builds on previous work
- Results are consolidated in **Phase 5** with cross-referenced findings
- The command uses **TodoWrite** to track progress through phases
- Especially useful before releases to prepare all release materials
- You can run individual agents if you need specific analysis only
- The phased approach ensures thoroughness while optimizing for speed

---

## Customization

To customize the agents or command:

1. **Edit command behavior**: Modify `.claude/commands/release.prepare.md`
2. **Adjust agent analysis**: Modify individual agent files in `.claude/agents/`
3. **Add new agents**: Create new `.md` files in `.claude/agents/`
4. **Create new commands**: Create new `.md` files in `.claude/commands/`

### Agent Naming Convention

Agents follow a namespace hierarchy:
- `release.pr-*` - PR analysis agents
- `release.use-case-examples.*` - Example generation pipeline
- `release.notes.*` - Release notes pipeline

---

## Integration with Existing Scripts

This complements the existing `scripts/generate_changelog_entries.py` script:

- **generate_changelog_entries.py**: Adds entries to package CHANGELOGs (per-package, automated)
- **/release.prepare command**: Comprehensive release preparation (cross-package, analysis + examples + notes)

Use both together for complete release management:
1. Run `/release.prepare` to get comprehensive analysis and materials
2. Use the script to add entries to individual package CHANGELOGs
3. Use the release notes from the command for announcements

---

## Architecture Highlights

### Why This Structure?

**Parallel PR Analysis**:
- 5 agents analyze different aspects simultaneously
- No dependencies between agents
- Faster execution
- `release.pr-reviewer` synthesizes all findings

**Sequential Pipelines**:
- Examples: Each stage refines and evaluates previous work
- Notes: Outline → Draft → Review ensures quality
- Clear progression of refinement

**Benefits**:
- Speed where possible (parallel)
- Quality where needed (sequential)
- Comprehensive coverage (11 specialized agents)
- Clear outputs for decision-making

---

## Agent Capabilities

### What Can Be Analyzed?

**PR Analysis Agents Can**:
- Quantify changes (commits, files, lines)
- Categorize by type and theme
- Validate standards compliance
- Assess code quality
- Identify risks and issues

**Example Agents Can**:
- Find new features needing examples
- Design complete example implementations
- Evaluate designs for quality
- Prioritize by impact and effort

**Notes Agents Can**:
- Structure comprehensive release notes
- Write engaging content with examples
- Review for accuracy and clarity
- Ensure publication readiness

---

## Contributing

When adding new commands or agents:

1. Use descriptive names with namespace prefixes
2. Include YAML frontmatter with `description`
3. Provide clear instructions and expected outputs
4. Follow the existing format and structure
5. Document execution patterns (parallel vs. sequential)
6. Test thoroughly before committing

---

## Learn More

- [Claude Code Documentation](https://docs.claude.com/en/docs/claude-code)
- [Slash Commands](https://docs.claude.com/en/docs/claude-code/slash-commands)
- [Agents](https://docs.claude.com/en/docs/claude-code/agents)
