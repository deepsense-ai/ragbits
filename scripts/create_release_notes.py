# /// script
# requires-python = ">=3.10"
# dependencies = [
# ]
# ///
# To run this script and create release notes, run the following command:
#
#   uv run scripts/create_release_notes.py
#
import re
import sys
from pathlib import Path

PACKAGES_DIR = Path(__file__).parent.parent / "packages"

# Sub-packages to aggregate (exclude the umbrella 'ragbits' package)
SUB_PACKAGES = [
    "ragbits-core",
    "ragbits-agents",
    "ragbits-chat",
    "ragbits-document-search",
    "ragbits-evaluate",
    "ragbits-guardrails",
    "ragbits-cli",
]


def extract_version_content(changelog_content: str, version: str | None = None) -> tuple[str | None, str | None]:
    """
    Extract version header and content from a CHANGELOG.md file.

    If version is None, extracts the latest version section.
    If version is provided, extracts the section for that specific version.

    Args:
        changelog_content: Content of the CHANGELOG.md file.
        version: Specific version to extract, or None for latest.

    Returns:
        Tuple of (version_number, version_header, content) or (None, None, None) if not found.
    """
    pattern = rf"## ({re.escape(version)}.*?)(?=\n## |\Z)" if version else r"## (\d+\.\d+\.\d+.*?)(?=\n## |\Z)"
    match = re.search(pattern, changelog_content, re.DOTALL)
    if not match:
        return None, None

    full_text = match.group(1).strip()
    version_header = full_text.split("\n")[0].strip()
    version_num = re.match(r"(\d+\.\d+\.\d+)", version_header)

    return (version_num.group(1), version_header, full_text) if version_num else (None, None, None)


def extract_meaningful_entries(content: str) -> str | None:
    """
    Extract meaningful changelog entries, filtering out generic dependency update lines.

    Args:
        content: Raw version section content.

    Returns:
        Filtered content with only meaningful entries, or None if nothing meaningful.
    """
    lines = content.split("\n")

    # Group lines by section (### headers), filtering out junk
    sections: dict[str, list[str]] = {}
    current_section = ""

    for line in lines[1:]:  # Skip the version header line
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r"^### .+$", stripped):
            current_section = stripped
            continue
        if re.match(r"^- .+ updated to version v\d+", stripped):
            continue
        sections.setdefault(current_section, []).append(line)

    if not sections:
        return None

    # Build output — include section headers when they exist in the changelog
    result_parts: list[str] = []

    for header, entries in sections.items():
        if not entries:
            continue
        if header:
            result_parts.append(f"\n{header}\n")
        result_parts.extend(entries)

    if not result_parts:
        return None

    return "\n".join(result_parts).strip()


def create_release_notes(package: str = "ragbits", version: str | None = None) -> None:
    """
    Create a RELEASE_NOTES.md file by aggregating changelogs from all sub-packages.

    Args:
        package: Umbrella package name.
        version: Specific version to generate notes for, or None for latest.
    """
    # Get the version from the umbrella changelog if not specified
    umbrella_changelog = PACKAGES_DIR / package / "CHANGELOG.md"
    if not umbrella_changelog.exists():
        print("Error: Umbrella CHANGELOG.md not found!")
        return

    if not version:
        version, version_header, _ = extract_version_content(umbrella_changelog.read_text())
    else:
        _, version_header, _ = extract_version_content(umbrella_changelog.read_text(), version)
    if not version or not version_header:
        print("Error: No version information found in umbrella CHANGELOG.md!")
        return

    print(f"Creating release notes for {version_header}")

    # Aggregate entries from all sub-packages
    sections: list[str] = []
    for pkg_name in SUB_PACKAGES:
        changelog_path = PACKAGES_DIR / pkg_name / "CHANGELOG.md"
        if not changelog_path.exists():
            continue

        _, _, content = extract_version_content(changelog_path.read_text(), version)
        if not content:
            continue

        entries = extract_meaningful_entries(content)
        if not entries:
            continue

        sections.append(f"## {pkg_name}\n\n{entries}")

    # Build the release notes
    if sections:
        body = "\n\n".join(sections)
        release_notes = f"# {version_header}\n\n{body}\n"
    else:
        release_notes = f"# {version_header}\n\nNo notable changes in this release.\n"

    # Write to RELEASE_NOTES.md
    output_path = Path("RELEASE_NOTES.md")
    output_path.write_text(release_notes, encoding="utf-8")
    print(f"Successfully created {output_path}")


if __name__ == "__main__":
    version_arg = sys.argv[1] if len(sys.argv) > 1 else None
    create_release_notes(version=version_arg)
