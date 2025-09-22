# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "tomli",
# ]
# ///
# To run this script and check if a nightly build is needed, run the following command:
#
#   uv run scripts/check_nightly_build.py
#
# This script:
# 1. Gets the current commit hash
# 2. Checks if we already built this commit as a nightly
# 3. Generates a nightly version if build is needed
# 4. Outputs results in GitHub Actions format
#

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import tomli


def run_git_command(cmd: list[str]) -> str:
    """Run a git command and return the output."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)  # noqa: S603
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Git command failed: {' '.join(cmd)}")
        print(f"Error: {e.stderr}")
        sys.exit(1)


def get_current_commit_hash() -> str:
    """Get the current short commit hash."""
    return run_git_command(["git", "rev-parse", "--short", "HEAD"])


def get_current_full_commit_hash() -> str:
    """Get the current full commit hash."""
    return run_git_command(["git", "rev-parse", "HEAD"])


def get_last_nightly_tag() -> str | None:
    """Get the last nightly tag (contains 'dev')."""
    try:
        tags = run_git_command(["git", "tag", "-l", "*dev*", "--sort=-version:refname"])
        if tags:
            return tags.split("\n")[0]
        return None
    except subprocess.CalledProcessError:
        return None


def get_commit_for_tag(tag: str) -> str:
    """Get the commit hash that a tag points to."""
    return run_git_command(["git", "rev-list", "-n", "1", tag])


def get_base_version() -> str:
    """Get the base version from pyproject.toml, stripping any .dev part."""
    pyproject_path = Path("packages/ragbits/pyproject.toml")

    if not pyproject_path.exists():
        print(f"Error: {pyproject_path} not found")
        sys.exit(1)

    try:
        with open(pyproject_path, "rb") as f:
            data = tomli.load(f)
        version = data["project"]["version"]

        if ".dev" in version:
            version = version.split(".dev")[0]

        return version
    except (KeyError, tomli.TOMLDecodeError) as e:
        print(f"Error reading version from {pyproject_path}: {e}")
        sys.exit(1)


def generate_nightly_version(base_version: str) -> str:
    """Generate a nightly version using timestamp (PEP 440 compliant)."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    return f"{base_version}.dev{timestamp}"


def set_github_output(name: str, value: str) -> None:
    """Set GitHub Actions output variable."""
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"{name}={value}\n")

    print(f"OUTPUT: {name}={value}")


def main() -> None:
    """Main function to check if nightly build is needed."""
    # Get current commit info
    commit_hash = get_current_commit_hash()
    current_commit = get_current_full_commit_hash()

    set_github_output("commit-hash", commit_hash)

    print(f"Current commit: {commit_hash} ({current_commit})")

    # Check if we already built this commit as nightly
    last_nightly_tag = get_last_nightly_tag()

    if last_nightly_tag:
        print(f"Last nightly tag: {last_nightly_tag}")
        last_nightly_commit = get_commit_for_tag(last_nightly_tag)

        if current_commit == last_nightly_commit:
            print("No new commits since last nightly build")
            set_github_output("should-build", "false")
            return
    else:
        print("No previous nightly tags found")

    # Generate nightly version
    base_version = get_base_version()
    nightly_version = generate_nightly_version(base_version)

    print(f"Will build nightly version: {nightly_version}")

    set_github_output("should-build", "true")
    set_github_output("nightly-version", nightly_version)


if __name__ == "__main__":
    main()
