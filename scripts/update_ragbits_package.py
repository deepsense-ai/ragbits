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
# Root directory containing TypeScript workspaces
TS_PACKAGES_DIR = Path(__file__).parent.parent / "typescript"


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


def _add_updated_dependency_to_changelog(pkg_name: str, dependency_name: str, new_dependency_version: str) -> None:
    changelog_path = PACKAGES_DIR / pkg_name / "CHANGELOG.md"
    changelog_content = changelog_path.read_text()

    unreleased_match = re.search(r"^## Unreleased\s*$", changelog_content, re.MULTILINE)
    if unreleased_match:
        insert_index = unreleased_match.end()
        changelog_content = (
            changelog_content[:insert_index]
            + f"\n- {dependency_name} updated to version v{new_dependency_version}\n"
            + changelog_content[insert_index:]
        )

    changelog_path.write_text(changelog_content)


def _update_pkg_version(
    pkg_name: str,
    new_version: str | None = None,
) -> None:
    """Update a single package's version and all cross-references.

    Searches every pyproject.toml in PACKAGES_DIR for dependencies (both regular
    and optional) that reference ``pkg_name`` with a pinned ``==`` version and
    replaces them with the new version. Also adds a changelog entry for each
    affected package.
    """
    pkg_pyproject_path = PACKAGES_DIR / pkg_name / "pyproject.toml"
    pkg_pyproject = tomlkit.parse(pkg_pyproject_path.read_text())

    version = pkg_pyproject["project"]["version"]

    pkg_pyproject["project"]["version"] = new_version
    pkg_pyproject_path.write_text(tomlkit.dumps(pkg_pyproject))

    pprint(f"\n[green]The {pkg_name} package was successfully updated from {version} to {new_version}.[/green]")

    for pyproject_path in PACKAGES_DIR.rglob("pyproject.toml"):
        # Skip the package's own pyproject.toml
        if pyproject_path.parent.name == pkg_name:
            continue

        pyproject = tomlkit.parse(pyproject_path.read_text())
        changed = False

        # Update regular dependencies
        deps = pyproject.get("project", {}).get("dependencies", [])
        for i, dep in enumerate(deps):
            dep_base = re.split(r"[=\[><!~]", dep)[0]
            if dep_base == pkg_name and dep != f"{pkg_name}=={new_version}":
                deps[i] = f"{pkg_name}=={new_version}"
                changed = True

        # Update optional dependencies
        optional_deps = pyproject.get("project", {}).get("optional-dependencies", {})
        for extra_deps in optional_deps.values():
            for i, dep in enumerate(extra_deps):
                dep_base = re.split(r"[=\[><!~]", dep)[0]
                if dep_base == pkg_name:
                    # Preserve extras like pkg_name[extra]==version
                    extra_match = re.match(r"([^=\[]+)(\[[^\]]+\])?(.*)", dep)
                    if extra_match:
                        extras_part = extra_match.group(2) or ""
                        new_dep = f"{pkg_name}{extras_part}=={new_version}"
                        if dep != new_dep:
                            extra_deps[i] = new_dep
                            changed = True

        if changed:
            pyproject_path.write_text(tomlkit.dumps(pyproject))
            dependent_pkg = pyproject_path.parent.name
            _add_updated_dependency_to_changelog(dependent_pkg, pkg_name, new_version)
            pprint(f"[green]Updated references to {pkg_name} in {pyproject_path}[/green]")


def _create_changelog_release(pkg_name: str, new_version: str) -> None:
    changelog_path = PACKAGES_DIR / pkg_name / "CHANGELOG.md"
    changelog_content = changelog_path.read_text()
    changelog_content = changelog_content.replace(
        "## Unreleased", f"## Unreleased\n\n## {new_version} ({datetime.today().strftime('%Y-%m-%d')})"
    )
    changelog_path.write_text(changelog_content)


def _update_ts_packages_version(new_version: str) -> None:
    """Update the `version` field in every package.json under the `typescript` directory."""
    if not isinstance(new_version, str):
        raise TypeError("new_version must be a string")
    for package_json_path in TS_PACKAGES_DIR.rglob("package.json"):
        # Skip node_modules to avoid touching installed packages
        if "node_modules" in package_json_path.parts:
            continue

        file_lines = package_json_path.read_text().splitlines()
        updated = False
        old_version: str | None = None
        new_lines: list[str] = []

        for line in file_lines:
            new_line = line
            if '"version"' in line:
                # capture: "version": "1.2.3" (comma optional)
                left, right = line.split(":")
                start = right.index('"')
                end = right[start + 1 :].index('"') + start
                old_version = right[start + 1 : end + 1]
                new_line = ":".join([left, right[:start] + f'"{new_version}"' + right[end + 2 :]])
                updated = True
            new_lines.append(new_line)

        if updated:
            package_json_path.write_text("\n".join(new_lines) + "\n")
            pprint(f"[green]Updated {package_json_path} version from {old_version} to {new_version}.[/green]")


def _update_ragbits_extras(packages: list[str], new_version: str) -> None:
    """Rebuild ragbits/pyproject.toml optional-dependencies from subpackage extras."""
    ragbits_pyproject_path = PACKAGES_DIR / "ragbits" / "pyproject.toml"
    ragbits_pyproject_data = tomlkit.parse(ragbits_pyproject_path.read_text())

    new_extras: dict[str, tomlkit.items.Array] = {}

    for pkg in packages:
        pkg_pyproject_path = PACKAGES_DIR / pkg / "pyproject.toml"
        pkg_pyproject = tomlkit.parse(pkg_pyproject_path.read_text())

        if "optional-dependencies" in pkg_pyproject["project"]:
            for extra in pkg_pyproject["project"]["optional-dependencies"]:
                if extra not in new_extras:
                    arr = tomlkit.array()
                    arr.multiline(True)
                    new_extras[extra] = arr

                new_extras[extra].append(f"{pkg}[{extra}]=={new_version}")

    ragbits_pyproject_data["project"]["optional-dependencies"] = new_extras
    ragbits_pyproject_path.write_text(tomlkit.dumps(ragbits_pyproject_data))


def _update_ragbits(
    packages: list[str],
    new_version: str,
    user_prompt_required: bool,
) -> None:
    if user_prompt_required:
        print("When upgrading the ragbits package it is also necessary to upgrade all other packages.")
        is_continue = confirm(message="Do you want to continue?")
    else:
        is_continue = True

    if not is_continue:
        pprint("[red]The ragbits package was not successfully updated.[/red]")
        return

    for pkg in packages:
        _update_pkg_version(pkg, new_version=new_version)

    ragbits_pyproject_path = PACKAGES_DIR / "ragbits" / "pyproject.toml"

    ragbits_pyproject = tomlkit.parse(ragbits_pyproject_path.read_text())
    ragbits_pyproject["project"]["version"] = new_version

    ragbits_pyproject_path.write_text(tomlkit.dumps(ragbits_pyproject))
    pprint(f"\n[green]The ragbits package was successfully updated to {new_version}.[/green]")

    _update_ragbits_extras(packages, new_version)
    _update_ts_packages_version(new_version)


def run(
    pkg_name: str | None = typer.Argument(None),
    update_type: str | None = typer.Argument(None),
    base_version: str | None = typer.Argument(None),
) -> None:
    """
    Main entry point for the package version updater. Updates package versions based on user input.

    If the package is "ragbits", all packages will be updated to the same version.
    Otherwise, only the specified package and its cross-references are updated.

    Args:
        pkg_name: Name of the package to update. If not provided, the user is prompted.
        update_type: Type of version update to apply (major, minor or patch). If not provided,
        the user is prompted for this input.
        base_version: Base version to update from (used for releases). If not provided, uses
        the current version from the package's pyproject.toml.

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

    ragbits_pyproject = tomlkit.parse((PACKAGES_DIR / "ragbits" / "pyproject.toml").read_text())
    version = base_version if base_version else ragbits_pyproject["project"]["version"]

    if update_type is not None:
        new_version = _get_updated_version(version, casted_update_type)
    else:
        pprint(f"Current version is: [bold]{version}[/bold]")
        new_version = text(
            "Enter the new version",
            default=_get_updated_version(version, UpdateType.PATCH),
        )

    if not isinstance(new_version, str):
        raise TypeError("new_version must be a string")

    if pkg_name == "ragbits":
        packages.remove(pkg_name)
        _update_ragbits(packages, new_version, user_prompt_required)
    else:
        _update_pkg_version(pkg_name, new_version=new_version)
        packages = []

    packages.append(pkg_name)
    for pkg in packages:
        _create_changelog_release(pkg_name=pkg, new_version=new_version)


if __name__ == "__main__":
    typer.run(run)
