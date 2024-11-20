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
import re
from copy import deepcopy
from datetime import datetime
from enum import Enum
from pathlib import Path

import tomlkit  # type: ignore
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


def _update_type_to_enum(update_type: str | None = None) -> UpdateType | None:
    if update_type is not None:
        return UpdateType(update_type)
    return None


def _version_to_list(version_string: str) -> list[int]:
    return [int(part) for part in version_string.split(".")]


def _check_update_type(version: str, new_version: str) -> UpdateType:
    version_list = _version_to_list(version)
    new_version_list = _version_to_list(new_version)

    if version_list[0] != new_version_list[0]:
        return UpdateType.MAJOR
    if version_list[1] != new_version_list[1]:
        return UpdateType.MINOR
    return UpdateType.PATCH


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
    pkg_pyproject: tomlkit.TOMLDocument | None = None,
    new_version: str | None = None,
    update_type: UpdateType | None = None,
    sync_ragbits_version: bool = False,
) -> tuple[str, str]:
    if not pkg_pyproject:
        pkg_pyproject = tomlkit.parse((PACKAGES_DIR / pkg_name / "pyproject.toml").read_text())

    version = pkg_pyproject["project"]["version"]

    if not new_version:
        if update_type is not None:
            new_version = _get_updated_version(version, update_type=update_type)
        else:
            pprint(f"Current version of the [bold]{pkg_name}[/bold] package is: [bold]{version}[/bold]")
            new_version = text(
                "Enter the new version",
                default=_get_updated_version(version, UpdateType.PATCH),
            )

    pkg_pyproject["project"]["version"] = new_version
    (PACKAGES_DIR / pkg_name / "pyproject.toml").write_text(tomlkit.dumps(pkg_pyproject))

    if not isinstance(new_version, str):
        raise TypeError("new_version must be a string")
    pprint(f"[green]The {pkg_name} package was successfully updated from {version} to {new_version}.[/green]")

    if pkg_name != "ragbits":
        _sync_ragbits_deps(pkg_name, version, new_version, sync_ragbits_version)

    _create_changelog_release(pkg_name=pkg_name, new_version=new_version)

    return version, new_version


def _sync_ragbits_deps(pkg_name: str, pkg_version: str, pkg_new_version: str, update_version: bool = True) -> None:
    ragbits_pkg_project = tomlkit.parse((PACKAGES_DIR / "ragbits" / "pyproject.toml").read_text())
    ragbits_deps: list[str] = [dep.split("==")[0] for dep in ragbits_pkg_project["project"]["dependencies"]]

    update_type = _check_update_type(pkg_version, pkg_new_version)

    if pkg_name in ragbits_deps:
        idx = ragbits_pkg_project["project"]["dependencies"].index(f"{pkg_name}=={pkg_version}")
        del ragbits_pkg_project["project"]["dependencies"][idx]
        ragbits_pkg_project["project"]["dependencies"].insert(idx, f"{pkg_name}=={pkg_new_version}")
        _add_updated_dependency_to_changelog("ragbits", pkg_name, pkg_new_version)

        if update_version:
            ragbits_old_version = ragbits_pkg_project["project"]["version"]
            ragbits_new_version = _get_updated_version(ragbits_old_version, update_type=update_type)
            ragbits_pkg_project["project"]["version"] = ragbits_new_version

            pprint(
                "[green]The ragbits package was successfully updated "
                f"from {ragbits_old_version} to {ragbits_new_version}.[/green]"
            )
            _create_changelog_release(pkg_name="ragbits", new_version=ragbits_new_version)

        (PACKAGES_DIR / "ragbits" / "pyproject.toml").write_text(tomlkit.dumps(ragbits_pkg_project))


def _add_updated_dependency_to_changelog(pkg_name: str, dependency_name: str, new_dependency_version: str) -> None:
    changelog_path = PACKAGES_DIR / pkg_name / "CHANGELOG.md"
    changelog_content = changelog_path.read_text()

    # Find the "## Unreleased" section
    unreleased_match = re.search(r"^## Unreleased\s*$", changelog_content, re.MULTILINE)
    if unreleased_match:
        unreleased_index = unreleased_match.end()

        # Find the next section after "## Unreleased"
        next_section_match = re.search(r"^##\s", changelog_content[unreleased_index:], re.MULTILINE)
        next_section_index = (
            unreleased_index + next_section_match.start() if next_section_match else len(changelog_content)
        )

        # Check if "### Changed" exists in the "## Unreleased" section
        changed_match = re.search(
            r"^### Changed\s*$", changelog_content[unreleased_index:next_section_index], re.MULTILINE
        )
        if not changed_match:
            # If "### Changed" does not exist, create it above any existing sections
            changelog_content = (
                changelog_content[:unreleased_index]
                + f"\n### Changed\n\n- {dependency_name} updated to version v{new_dependency_version}\n"
                + changelog_content[unreleased_index:]
            )
        else:
            # If "### Changed" exists, append the new entry
            changed_index = unreleased_index + changed_match.end()
            changelog_content = (
                changelog_content[:changed_index]
                + f"\n- {dependency_name} updated to version v{new_dependency_version}"
                + changelog_content[changed_index:]
            )

    changelog_path.write_text(changelog_content)


def _create_changelog_release(pkg_name: str, new_version: str) -> None:
    changelog_path = PACKAGES_DIR / pkg_name / "CHANGELOG.md"
    changelog_content = changelog_path.read_text()
    changelog_content = changelog_content.replace(
        "## Unreleased", f"## Unreleased\n\n## {new_version} ({datetime.today().strftime('%Y-%m-%d')})"
    )
    changelog_path.write_text(changelog_content)


def _update_ragbits_extras(packages: list[str]) -> None:
    subpackages = [pkg for pkg in packages if pkg != "ragbits"]

    extras = {}
    for pkg in subpackages:
        pkg_pyproject_path = PACKAGES_DIR / pkg / "pyproject.toml"
        pkg_pyproject = tomlkit.parse(pkg_pyproject_path.read_text())

        if "optional-dependencies" in pkg_pyproject["project"]:
            for extra, deps in pkg_pyproject["project"]["optional-dependencies"].items():
                if extra in extras and extras[extra] != deps:
                    raise Exception(
                        f"Duplicate extras: '{extra}' exists in multiple packages with different dependencies."
                    )
                extras[extra] = deps

    extras = dict(sorted(extras.items()))

    ragbits_pyproject_path = PACKAGES_DIR / "ragbits" / "pyproject.toml"
    ragbits_pyproject_data = tomlkit.parse(ragbits_pyproject_path.read_text())

    for extra, deps in extras.items():
        ragbits_pyproject_data["project"]["optional-dependencies"][extra] = deps

    ragbits_pyproject_path.write_text(tomlkit.dumps(ragbits_pyproject_data))


def run(pkg_name: str | None = typer.Argument(None), update_type: str | None = typer.Argument(None)) -> None:
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
        _update_ragbits_extras(packages)

    elif pkg_name == "ragbits-core":
        if user_prompt_required:
            print("When upgrading the ragbits-core package it is also necessary to upgrade the other packages.")
            is_continue = confirm(message="Do you want to continue?")
        else:
            is_continue = True

        if is_continue:
            version, new_version = _update_pkg_version(pkg_name, update_type=casted_update_type)
            casted_update_type = _check_update_type(version, new_version)

            for pkg in sorted([pkg for pkg in packages if pkg != "ragbits-core"], reverse=True):
                pkg_pyproject = tomlkit.parse((PACKAGES_DIR / pkg / "pyproject.toml").read_text())
                pkg_pyproject["project"]["dependencies"] = [
                    dep for dep in pkg_pyproject["project"]["dependencies"] if "ragbits-core" not in dep
                ]
                pkg_pyproject["project"]["dependencies"].append(f"ragbits-core=={new_version}")
                if pkg != "ragbits":
                    _add_updated_dependency_to_changelog(pkg, pkg_name, new_version)
                _update_pkg_version(pkg, pkg_pyproject, update_type=casted_update_type)

        else:
            pprint("[red]The ragbits-core package was not successfully updated.[/red]")

    else:
        _update_pkg_version(pkg_name, update_type=casted_update_type, sync_ragbits_version=True)


if __name__ == "__main__":
    typer.run(run)
