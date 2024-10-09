# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "tomlkit",
#     "inquirer",
#     "rich",
#     "typing-extensions",
#     "typer"
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
import typer
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


def _update_type_to_enum(update_type: Optional[str] = None) -> Optional[UpdateType]:
    if update_type is not None:
        return UpdateType(update_type)
    return None


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


def _get_updated_version(version: str, update_type: UpdateType) -> str:
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
        if update_type is not None:
            new_version = _get_updated_version(version, update_type=update_type)
        else:
            pprint(f"Current version of the [bold]{pkg_name}[/bold] package is: [bold]{version}[/bold]")
            new_version = text("Enter the new version", default=_get_updated_version(version, UpdateType.PATCH))

    pkg_pyproject["project"]["version"] = new_version
    (PACKAGES_DIR / pkg_name / "pyproject.toml").write_text(tomlkit.dumps(pkg_pyproject))

    assert isinstance(new_version, str)
    pprint(f"[green]The {pkg_name} package was successfully updated from {version} to {new_version}.[/green]")

    return version, new_version


def _sync_ragbits_deps(pkg_name: str, pkg_version: str, pkg_new_version: str, update_type: UpdateType):
    ragbits_pkg_project = tomlkit.parse((PACKAGES_DIR / "ragbits/pyproject.toml").read_text())
    ragbits_deps: list[str] = [dep.split("==")[0] for dep in ragbits_pkg_project["project"]["dependencies"]]

    if pkg_name in ragbits_deps:
        idx = ragbits_pkg_project["project"]["dependencies"].index(f"{pkg_name}=={pkg_version}")
        del ragbits_pkg_project["project"]["dependencies"][idx]
        ragbits_pkg_project["project"]["dependencies"].insert(idx, f"{pkg_name}=={pkg_new_version}")

        ragbits_old_version = ragbits_pkg_project["project"]["version"]
        ragbits_new_version = _get_updated_version(ragbits_old_version, update_type=update_type)
        ragbits_pkg_project["project"]["version"] = ragbits_new_version

        (PACKAGES_DIR / "ragbits" / "pyproject.toml").write_text(tomlkit.dumps(ragbits_pkg_project))
        pprint(
            "[green]The ragbits package was successfully updated "
            f"from {ragbits_old_version} to {ragbits_new_version}.[/green]"
        )


def run(pkg_name: Optional[str] = typer.Argument(None), update_type: Optional[str] = typer.Argument(None)) -> None:
    """
    Main entry point for the package version updater. Updates package versions based on user input.

    Based on the provided package name and update type, this function updates the version of a
    specific package. If the package is "ragbits-core", all other packages that depend on it
    will also be updated accordingly.

    If no package name or update type is provided, the user will be prompted to select a package
    and version update type interactively. For "ragbits-core", the user is asked for confirmation
    before proceeding with a global update.

    Args:
        pkg_name: Name of the package to update. If not provided, the user is prompted.
        update_type: Type of version update to apply (major, minor or patch). If not provided,
        the user is prompted for this input.

    Raises:
        ValueError: If the provided `pkg_name` is not found in the available packages.
    """

    packages: list[str] = [obj.name for obj in PACKAGES_DIR.iterdir() if obj.is_dir()]

    if pkg_name is not None:
        if pkg_name not in packages:
            raise ValueError(f"Package '{pkg_name}' not found in available packages.")
    else:
        pkg_name = list_input("Enter the package name", choices=packages)

    casted_update_type = _update_type_to_enum(update_type)

    user_prompt_required = pkg_name is None or casted_update_type is None

    if pkg_name == "ragbits":
        _update_pkg_version(pkg_name, update_type=casted_update_type)

    elif pkg_name == "ragbits-core":
        if user_prompt_required:
            print("When upgrading the ragbits-core package it is also necessary to upgrade the other packages.")
            is_continue = confirm(message="Do you want to continue?")
        else:
            is_continue = True

        if is_continue:
            version, new_version = _update_pkg_version(pkg_name, update_type=casted_update_type)
            casted_update_type = _check_update_type(version, new_version)

            for pkg in [pkg for pkg in packages if pkg != "ragbits-core"]:
                pkg_pyproject = tomlkit.parse((PACKAGES_DIR / pkg / "pyproject.toml").read_text())
                pkg_pyproject["project"]["dependencies"] = [
                    dep for dep in pkg_pyproject["project"]["dependencies"] if "ragbits-core" not in dep
                ]
                pkg_pyproject["project"]["dependencies"].append(f"ragbits-core=={new_version}")
                _update_pkg_version(pkg, pkg_pyproject, update_type=casted_update_type)

        else:
            pprint("[red]The ragbits-core package was not successfully updated.[/red]")

    else:
        version, new_version = _update_pkg_version(pkg_name, update_type=casted_update_type)
        _sync_ragbits_deps(pkg_name, version, new_version, update_type)


if __name__ == "__main__":
    typer.run(run)
