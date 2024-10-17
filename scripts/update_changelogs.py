# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "tomlkit",
# ]
# ///
# To run this script and update changelogs, run the following command:
#
#   uv run scripts/update_changelogs.py
#

from pathlib import Path


PACKAGES_DIR = Path(__file__).parent.parent / "packages"


def run() -> None:
    """
    Update changelogs for all packages.
    """
    for package_dir in PACKAGES_DIR.iterdir():
        changelog_path = package_dir / "CHANGELOG.md"
        if not changelog_path.exists():
            print(f"Changelog for {package_dir.name} does not exist")
            continue

        changelog = changelog_path.read_text()
        changelog_lines = changelog.splitlines()

        new_changelog_lines = [changelog_lines[0]]

