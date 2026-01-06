# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "tomlkit",
# ]
# ///
"""
Script to update all package versions in the workspace for nightly builds.

Usage:
    uv run scripts/update_nightly_versions.py "1.2.3.dev20250109a1b2c3d"
"""

import sys
from pathlib import Path

import tomlkit  # type: ignore


def update_package_version(package_dir: Path, new_version: str) -> None:
    """
    Update the version in a package's pyproject.toml file.

    Args:
        package_dir: Path to the package directory
        new_version: New version string to set
    """
    pyproject_path = package_dir / "pyproject.toml"

    if not pyproject_path.exists():
        print(f"Warning: {pyproject_path} not found, skipping")
        return

    # Read current pyproject.toml
    data = tomlkit.parse(pyproject_path.read_text())

    # Update version
    if (project := data.get("project")) and "version" in project:
        old_version = project["version"]
        project["version"] = new_version
        print(f"Updated {package_dir.name}: {old_version} → {new_version}")
    else:
        print(f"Warning: No version field found in {pyproject_path}")
        return

    # Update dependencies to use the same nightly version
    if dependencies := project.get("dependencies"):
        for i, dep in enumerate(dependencies):
            if dep.startswith("ragbits-") and "==" in dep:
                package_name = dep.split("==")[0]
                dependencies[i] = f"{package_name}=={new_version}"
                print(f"Updated dependency in {package_dir.name}: {package_name}=={new_version}")

    # Update optional-dependencies (extras) to use the same nightly version
    if optional_deps := project.get("optional-dependencies"):
        for extra_name, deps in optional_deps.items():
            for i, dep in enumerate(deps):
                if dep.startswith("ragbits-") and "==" in dep:
                    # Extract package name with or without extras
                    package_part = dep.split("==")[0]
                    deps[i] = f"{package_part}=={new_version}"
                    print(f"Updated extra '{extra_name}' in {package_dir.name}: {package_part}=={new_version}")

    # Write updated pyproject.toml
    pyproject_path.write_text(tomlkit.dumps(data))


def main() -> None:
    """Main function to update all package versions."""
    if len(sys.argv) != 2:  # noqa: PLR2004
        print("Usage: python update_nightly_versions.py <new_version>")
        print("Example: python update_nightly_versions.py '1.2.3.dev20250109a1b2c3d'")
        sys.exit(1)

    new_version = sys.argv[1]

    # Find all package directories
    workspace_root = Path(__file__).parent.parent
    packages_dir = workspace_root / "packages"

    if not packages_dir.exists():
        print(f"Error: Packages directory not found at {packages_dir}")
        sys.exit(1)

    # Get list of package directories
    package_dirs = [d for d in packages_dir.iterdir() if d.is_dir() and (d / "pyproject.toml").exists()]

    if not package_dirs:
        print("Error: No package directories with pyproject.toml found")
        sys.exit(1)

    print(f"Updating {len(package_dirs)} packages to version {new_version}")

    # Update each package
    for package_dir in sorted(package_dirs):
        update_package_version(package_dir, new_version)

    print(f"Successfully updated all packages to version {new_version}")


if __name__ == "__main__":
    main()
