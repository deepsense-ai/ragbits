# Claude Code Configuration

This directory contains custom commands and agents for Claude Code to help with changelog generation and code quality validation.

## Commands

### `/changelog`

Generates a comprehensive changelog analysis with parallel agents examining changes since the last stable release.

**Usage**:
```
/changelog
```

**What it does** (4 phases):

**Phase 1: Determine Base Reference**
- Identifies the last stable version from CHANGELOG.md files
- Reports commit count and date range to analyze

**Phase 2: Launch Parallel Analysis**
- Launches 5 specialized agents simultaneously:
  - **changelog-summarizer**: Categorizes and summarizes all changes
  - **example-generator**: Suggests examples for new features
  - **commit-validator**: Validates commit message standards
  - **style-validator**: Checks code style consistency
  - **changelog-post-writer**: Writes comprehensive release announcement

**Phase 3: Review and Consolidate**
- Aggregates agent outputs
- Identifies common themes and conflicts
- Highlights critical issues and breaking changes

**Phase 4: Generate Final Output**
- Presents comprehensive report with:
  - 📊 Changelog summary (categorized by type and package)
  - 💡 Example ideas for new features
  - ✅ Commit message compliance report
  - 🎨 Code style validation
  - 📝 Release notes draft
  - 🎯 Actionable next steps

**Output**: Publication-ready changelog analysis with actionable recommendations

## Agents

### `changelog-summarizer`

Analyzes git history and categorizes commits by type (feat, fix, refactor, etc.) and package.

**Output**: Structured changelog with:
- Changes by category
- Changes by package
- Key themes and highlights
- Impact assessment

### `example-generator`

Identifies new features and suggests practical examples to demonstrate them.

**Output**: Example ideas with:
- Feature descriptions
- Implementation outlines
- Target difficulty levels
- Learning objectives

### `commit-validator`

Validates that commit messages follow conventional commit standards.

**Output**: Validation report with:
- Compliance statistics
- Issues found (critical, warnings, info)
- Common problems
- Recommendations
- Exemplary commits

### `style-validator`

Checks code changes for style consistency and adherence to project standards (ruff, mypy, pytest).

**Output**: Validation report with:
- Style consistency assessment
- Type hint coverage
- Documentation quality
- Testing standards
- Recommendations

### `changelog-post-writer`

Writes a comprehensive, user-friendly changelog post for release announcements.

**Output**: Complete release notes with:
- Overview and highlights
- Feature descriptions with examples
- Breaking changes with migration guides
- Statistics and resources
- Social media blurbs

## Project Standards

This project follows:

- **Commit Messages**: Conventional Commits format (`type(scope): description`)
- **Code Style**: ruff (120 char lines, PEP 8 based)
- **Type Checking**: mypy with strict mode for `ragbits.*`
- **Testing**: pytest with async support
- **Docstrings**: Google style convention

## Examples

### Analyzing Changes

To analyze all changes since the last release and generate a changelog:

```
/changelog
```

The command follows a structured 4-phase workflow:
1. **Phase 1**: Determines base reference (last stable version like 1.3.0)
2. **Phase 2**: Launches 5 agents in parallel to analyze changes
3. **Phase 3**: Consolidates findings and identifies key insights
4. **Phase 4**: Presents comprehensive report with actionable items

The workflow ensures thorough analysis while maintaining efficiency through parallel agent execution.

### Manual Agent Usage

You can also run individual agents directly using the Task tool if you need specific analysis:

```
Launch the changelog-summarizer agent to analyze commits since develop branch
```

## Tips

- The `/changelog` command follows a **phased workflow** for systematic analysis
- **Phase 2** runs all agents in **parallel** for maximum efficiency
- Each agent provides a unique perspective on the same changes
- Results are consolidated in **Phase 3** to identify patterns and conflicts
- The command uses **TodoWrite** to track progress through phases
- Especially useful before releases to prepare comprehensive release notes
- You can use this iteratively: run the command, make improvements, run again
- The phased approach ensures nothing is missed while maintaining speed

## Customization

To customize the agents or command:

1. **Edit command behavior**: Modify `.claude/commands/changelog.md`
2. **Adjust agent analysis**: Modify individual agent files in `.claude/agents/`
3. **Add new agents**: Create new `.md` files in `.claude/agents/`
4. **Add new commands**: Create new `.md` files in `.claude/commands/`

## Integration with Existing Scripts

This complements the existing `scripts/generate_changelog_entries.py` script:

- **generate_changelog_entries.py**: Adds entries to package CHANGELOGs (per-package, automated)
- **/changelog command**: Comprehensive analysis for release preparation (cross-package, manual review)

Use both together for complete changelog management:
1. Run `/changelog` to get comprehensive analysis
2. Use the script to add entries to individual package CHANGELOGs
3. Use the changelog post for release announcements

## Contributing

When adding new commands or agents:

1. Use descriptive names (kebab-case)
2. Include YAML frontmatter with `description`
3. Provide clear instructions and expected outputs
4. Follow the existing format and structure
5. Test thoroughly before committing

## Learn More

- [Claude Code Documentation](https://docs.claude.com/en/docs/claude-code)
- [Slash Commands](https://docs.claude.com/en/docs/claude-code/slash-commands)
- [Agents](https://docs.claude.com/en/docs/claude-code/agents)
