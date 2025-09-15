# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "tomlkit",
# ]
# ///
"""
Script to update all package versions in develop branch after a release.

Usage:
    uv run scripts/update_develop_versions.py "1.3.0"
"""

import sys
from pathlib import Path

import tomlkit  # type: ignore


def update_package_version(package_dir: Path, new_base_version: str) -> None:
    """
    Update the version in a package's pyproject.toml file to a new base version.

    Args:
        package_dir: Path to the package directory
        new_base_version: New base version string to set (e.g., "1.3.0")
    """
    pyproject_path = package_dir / "pyproject.toml"

    if not pyproject_path.exists():
        print(f"Warning: {pyproject_path} not found, skipping")
        return

    # Read current pyproject.toml
    data = tomlkit.parse(pyproject_path.read_text())

    # Update version
    if "project" in data and "version" in data["project"]:
        old_version = data["project"]["version"]
        data["project"]["version"] = new_base_version
        print(f"Updated {package_dir.name}: {old_version} → {new_base_version}")
    else:
        print(f"Warning: No version field found in {pyproject_path}")
        return

    # Update dependencies to use the same base version (without .dev suffix)
    if "project" in data and "dependencies" in data["project"]:
        dependencies = data["project"]["dependencies"]
        for i, dep in enumerate(dependencies):
            if dep.startswith("ragbits-") and ("==" in dep):
                package_name = dep.split("==")[0]
                dependencies[i] = f"{package_name}=={new_base_version}"
                print(f"Updated dependency in {package_dir.name}: {package_name}=={new_base_version}")

    # Write updated pyproject.toml
    pyproject_path.write_text(tomlkit.dumps(data))


def main() -> None:
    """Main function to update all package versions to new base version."""
    if len(sys.argv) != 2:  # noqa: PLR2004
        print("Usage: python update_develop_versions.py <new_base_version>")
        print("Example: python update_develop_versions.py '1.3.0'")
        sys.exit(1)

    new_base_version = sys.argv[1]

    # Validate version format
    version_parts = new_base_version.split(".")
    if len(version_parts) != 3 or not all(part.isdigit() for part in version_parts):  # noqa: PLR2004
        print(f"Error: Invalid version format '{new_base_version}'. Expected format: X.Y.Z")
        sys.exit(1)

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

    print(f"Updating {len(package_dirs)} packages to base version {new_base_version}")

    # Update each package
    for package_dir in sorted(package_dirs):
        update_package_version(package_dir, new_base_version)

    print(f"Successfully updated all packages to base version {new_base_version}")
    print("Nightly builds will now use format: {base_version}.devYYYYMMDDcommit")


if __name__ == "__main__":
    main()
