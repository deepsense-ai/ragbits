# Ragbits CLI

Ragbits comes with a command-line interface (CLI) that provides several commands for working with the Ragbits platform. It can be accessed by running the `ragbits` command in your terminal.

Commands that operate on Ragbits components, such as [`ragbits vector-store`](#ragbits-vector-store), use the project's preferred component implementations if a component configuration is not explicitly provided. To learn how to set component preferences in your project, see the [How-To: Set preferred components in Ragbits project](../how-to/project/component_preferences.md) guide.

::: mkdocs-click
    :module: ragbits.cli
    :command: _click_app
    :prog_name: ragbits
    :style: table
    :list_subcommands: true
    :depth: 1