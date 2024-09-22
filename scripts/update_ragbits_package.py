# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "tomlkit",
#     "inquirer",
#     "rich"
# ]
# ///
# To run this script and update a package, run the following command:
#
#   uv run scripts/update_ragbits_package.py
#

from copy import deepcopy
from enum import Enum
from pathlib import Path
from typing import Optional

import tomlkit
from inquirer.shortcuts import confirm, list_input, text
from rich import print as pprint

PACKAGES_DIR = Path(__file__).parent.parent / "packages"


class UpdateType(Enum):
    """
    Enum representing the type of version update: major, minor, or patch.
    """

    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"


def _version_to_list(version_string):
    return [int(part) for part in version_string.split(".")]


def _check_update_type(version: str, new_version: str) -> Optional[UpdateType]:
    version_list = _version_to_list(version)
    new_version_list = _version_to_list(new_version)

    if version_list[0] != new_version_list[0]:
        return UpdateType.MAJOR
    if version_list[1] != new_version_list[1]:
        return UpdateType.MINOR
    if version_list[2] != new_version_list[2]:
        return UpdateType.PATCH
    return None


def _get_updated_version(version: str, update_type: UpdateType = UpdateType.PATCH) -> str:
    version_list = _version_to_list(version)

    if update_type == UpdateType.MAJOR:
        new_version_list = [version_list[0] + 1, 0, 0]
    elif update_type == UpdateType.MINOR:
        new_version_list = [version_list[0], version_list[1] + 1, 0]
    else:
        new_version_list = deepcopy(version_list)
        new_version_list[2] = new_version_list[2] + 1

    return ".".join([str(n) for n in new_version_list])


def _update_pkg_version(
    pkg_name: str,
    pkg_pyproject: Optional[tomlkit.TOMLDocument] = None,
    new_version: Optional[str] = None,
    update_type: Optional[UpdateType] = None,
) -> tuple[str, str]:
    if not pkg_pyproject:
        pkg_pyproject = tomlkit.parse((PACKAGES_DIR / pkg_name / "pyproject.toml").read_text())

    version = pkg_pyproject["project"]["version"]

    if not new_version:
        if update_type:
            new_version = _get_updated_version(version, update_type)
        else:
            pprint(f"Current version of the [bold]{pkg_name}[/bold] package is: [bold]{version}[/bold]")
            new_version = text("Enter the new version", default=_get_updated_version(version))

    pkg_pyproject["project"]["version"] = new_version
    (PACKAGES_DIR / pkg_name / "pyproject.toml").write_text(tomlkit.dumps(pkg_pyproject))

    assert isinstance(new_version, str)
    pprint(f"[green]The {pkg_name} package was successfully updated from {version} to {new_version}.[/green]")

    return version, new_version


def run() -> None:
    """
    Main entry point for the package version updater. Updates package versions based on user input.

    The user selects a package, and if it is 'ragbits-core', all packages are updated based on the version
    update of 'ragbits-core'. Otherwise, the selected package is updated individually.
    """

    packages: list[str] = [obj.name for obj in PACKAGES_DIR.iterdir() if obj.is_dir()]
    pkg_name: str = list_input("Enter the package name", choices=packages)

    if pkg_name == "ragbits-core":
        print("When upgrading the ragbits-core package it is also necessary to upgrade the other packages.")
        is_continue = confirm(message="Do you want to continue?")
        if is_continue:
            ragbits_version, new_ragbits_version = _update_pkg_version(pkg_name)
            update_type = _check_update_type(ragbits_version, new_ragbits_version)

            for pkg_name in [pkg for pkg in packages if pkg != "ragbits-core"]:
                pkg_pyproject = tomlkit.parse((PACKAGES_DIR / pkg_name / "pyproject.toml").read_text())
                pkg_pyproject["project"]["dependencies"] = [
                    dep for dep in pkg_pyproject["project"]["dependencies"] if "ragbits" not in dep
                ]
                pkg_pyproject["project"]["dependencies"].append(f"ragbits=={new_ragbits_version}")
                _update_pkg_version(pkg_name, pkg_pyproject, update_type=update_type)

        else:
            pprint("[red]The ragbits-core package was not successfully updated.[/red]")
    else:
        _update_pkg_version(pkg_name)


if __name__ == "__main__":
    run()
