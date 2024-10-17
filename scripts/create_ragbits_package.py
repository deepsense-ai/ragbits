# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "tomlkit",
#     "inquirer",
# ]
# ///
# To run this script and create a new package, run the following command:
#
#   uv run scripts/create_ragbits_package.py
#

from pathlib import Path

import tomlkit
from inquirer.shortcuts import text

PACKAGES_DIR = Path(__file__).parent.parent / "packages"


def run() -> None:
    """
    Create a new Ragbits package.
    """
    package_name: str = text("Enter the package name", default="ragbits-")

    package_dir = PACKAGES_DIR / package_name

    if package_dir.exists():
        print(f"Package {package_name} already exists at {package_dir}")
        return

    package_dir.mkdir(exist_ok=True, parents=True)

    src_dir = package_dir / "src" / "ragbits" / package_name.removeprefix("ragbits-").replace("-", "_")
    src_dir.mkdir(exist_ok=True, parents=True)
    (src_dir / "__init__.py").touch()

    tests_dir = package_dir / "tests"
    tests_dir.mkdir(exist_ok=True)

    pkg_pyproject = tomlkit.parse((PACKAGES_DIR / "ragbits-core" / "pyproject.toml").read_text())

    pkg_pyproject["project"]["name"] = package_name
    pkg_pyproject["project"]["dependencies"] = []
    pkg_pyproject["project"]["optional-dependencies"] = {}

    (package_dir / "pyproject.toml").write_text(tomlkit.dumps(pkg_pyproject))

    print(f"Package {package_name} created at {package_dir}")

    workspace_pyproject_path = PACKAGES_DIR.parent / "pyproject.toml"
    workspace_pyproject = tomlkit.parse(workspace_pyproject_path.read_text())

    workspace_pyproject["project"]["dependencies"].append(package_name)

    workspace_info = tomlkit.inline_table()
    workspace_info.update({"workspace": True})

    workspace_pyproject["tool"]["uv"]["sources"][package_name] = workspace_info

    workspace_pyproject["tool"]["uv"]["workspace"]["members"].append(f"packages/{package_name}")
    workspace_pyproject["tool"]["mypy"]["mypy_path"].append(f"packages/{package_name}/src")

    workspace_pyproject_path.write_text(tomlkit.dumps(workspace_pyproject), encoding="utf-8")

    print(f"Package {package_name} added to the workspace")


if __name__ == "__main__":
    run()
