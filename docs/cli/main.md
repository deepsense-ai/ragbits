# Ragbits CLI

Ragbits comes with a command line interface (CLI) that provides a number of commands for working with the Ragbits platform. It can be accessed by running the `ragbits` command in your terminal.

Functions that operate on Ragbits components (like [`ragbits vector-store`](#ragbits-vector-store)) try to use default values for the components if they are not provided explicitly. To learn how to set these defaults in your project, see the [How to Set Default Configuration for Components](../how-to/core/configuration.md) guide.

::: mkdocs-click
    :module: ragbits.cli
    :command: _click_app
    :prog_name: ragbits
    :style: table
    :list_subcommands: true
    :depth: 1