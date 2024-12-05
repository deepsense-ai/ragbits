# /// script
# requires-python = ">=3.10"
# dependencies = [
# ]
# ///
# To run this script and create a new package, run the following command:
#
#   uv run scripts/create_ragbits_package.py
#
import re
from pathlib import Path


def extract_latest_version_content(changelog_content: str) -> str | None:
    """
    Extract the content of the latest version section from the CHANGELOG.md file.

    Args:
        changelog_content: Content of the CHANGELOG.md file.

    Returns:
        Content of the latest version section.
    """
    # Find all version sections
    version_pattern = r"## (\d+\.\d+\.\d+.*?)(?=\n## |\Z)"
    versions = re.finditer(version_pattern, changelog_content, re.DOTALL)

    # Get the first (latest) version section
    try:
        latest_version = next(versions)
        return latest_version.group(1).strip().replace("### ", "## ")
    except StopIteration:
        return None


def create_release_notes(package: str = "ragbits") -> None:
    """
    Create a RELEASE_NOTES.md file for the specified package.

    Args:
        package: Package name.
    """
    try:
        changelog_file = Path(__file__).parent.parent / "packages" / package / "CHANGELOG.md"
        changelog_content = changelog_file.read_text()
    except FileNotFoundError:
        print("Error: CHANGELOG.md file not found!")
        return

    # Extract the latest version content
    latest_version_content = extract_latest_version_content(changelog_content)

    if not latest_version_content:
        print("Error: No version information found in CHANGELOG.md!")
        return

    # Create RELEASE_NOTES.md content
    release_notes_content = f"# {latest_version_content}"

    # Write to RELEASE_NOTES.md
    try:
        with open("RELEASE_NOTES.md", "w", encoding="utf-8") as file:
            file.write(release_notes_content)
        print("Successfully created RELEASE_NOTES.md")
    except Exception as e:
        print(f"Error writing to RELEASE_NOTES.md: {str(e)}")


if __name__ == "__main__":
    create_release_notes()
