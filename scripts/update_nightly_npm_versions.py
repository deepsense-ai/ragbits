# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Script to update npm package versions in the workspace for nightly builds.

Usage:
    uv run scripts/update_nightly_npm_versions.py "1.2.3.dev202501090215"

This script:
1. Accepts a PEP 440 nightly version (e.g., "1.2.3.dev202501090215")
2. Converts it to npm-compatible semver format (e.g., "1.2.3-nightly.202501090215")
3. Updates package.json files for all @ragbits npm packages
4. Updates internal dependencies to use the nightly version
"""

import json
import sys
from pathlib import Path


def convert_to_npm_version(pep440_version: str) -> str:
    """
    Convert a PEP 440 nightly version to npm-compatible semver format.

    Args:
        pep440_version: PEP 440 version string (e.g., "1.2.3.dev202501090215")

    Returns:
        npm-compatible semver version (e.g., "1.2.3-dev.202501090215")
    """
    if ".dev" in pep440_version:
        base_version, dev_suffix = pep440_version.split(".dev")
        return f"{base_version}-dev.{dev_suffix}"
    return pep440_version


def update_package_json(package_dir: Path, new_version: str) -> None:
    """
    Update the version in a package's package.json file.

    Args:
        package_dir: Path to the package directory
        new_version: New npm-compatible version string to set
    """
    package_json_path = package_dir / "package.json"

    if not package_json_path.exists():
        print(f"Warning: {package_json_path} not found, skipping")
        return

    # Read current package.json
    with open(package_json_path, encoding="utf-8") as f:
        data = json.load(f)

    old_version = data.get("version", "unknown")
    data["version"] = new_version
    print(f"Updated {package_dir.name}: {old_version} → {new_version}")

    # Update @ragbits/* dependencies to use the nightly version
    if "dependencies" in data:
        for dep_name in data["dependencies"]:
            if dep_name.startswith("@ragbits/"):
                data["dependencies"][dep_name] = new_version
                print(f"Updated dependency in {package_dir.name}: {dep_name}@{new_version}")

    # Write updated package.json with proper formatting
    with open(package_json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
        f.write("\n")  # Ensure trailing newline


def main() -> None:
    """Main function to update all npm package versions."""
    if len(sys.argv) != 2:  # noqa: PLR2004
        print("Usage: python update_nightly_npm_versions.py <pep440_version>")
        print("Example: python update_nightly_npm_versions.py '1.2.3.dev202501090215'")
        sys.exit(1)

    pep440_version = sys.argv[1]
    npm_version = convert_to_npm_version(pep440_version)

    print(f"Converting PEP 440 version '{pep440_version}' to npm version '{npm_version}'")

    # Find npm package directories
    workspace_root = Path(__file__).parent.parent
    npm_packages_dir = workspace_root / "typescript" / "@ragbits"

    if not npm_packages_dir.exists():
        print(f"Error: npm packages directory not found at {npm_packages_dir}")
        sys.exit(1)

    # Get list of package directories
    package_dirs = [d for d in npm_packages_dir.iterdir() if d.is_dir() and (d / "package.json").exists()]

    if not package_dirs:
        print("Error: No package directories with package.json found")
        sys.exit(1)

    print(f"Updating {len(package_dirs)} npm packages to version {npm_version}")

    # Update each package
    for package_dir in sorted(package_dirs):
        update_package_json(package_dir, npm_version)

    print(f"Successfully updated all npm packages to version {npm_version}")


if __name__ == "__main__":
    main()
