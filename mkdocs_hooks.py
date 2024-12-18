from typing import Literal

from ragbits import cli


def on_startup(command: Literal["build", "gh-deploy", "serve"], dirty: bool) -> None:
    """
    Hook that runs during mkdocs startup.

    Args:
        command: The command that is being run.
        dirty: whether --dirty flag was passed.
    """
    cli._init_for_mkdocs()
