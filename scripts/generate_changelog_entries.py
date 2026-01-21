#!/usr/bin/env uv run
# /// script
# dependencies = [
#     "rich>=13.0.0",
# ]
# ///

import asyncio
import re
import shlex
import subprocess
import sys

from rich import box
from rich.console import Console
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"❌ {message}", style="bold red")


def run_git_command(cmd: str) -> str:
    """Run a git command and return the output."""
    try:
        result = subprocess.run(shlex.split(cmd), capture_output=True, text=True, check=True)  # noqa: S603
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print_error(f"Git command failed: {cmd}")
        print_error(f"Error: {e.stderr}")
        return ""


def get_changed_packages(base_branch: str) -> list[str]:
    """Get list of packages that have changes compared to base branch."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task1 = progress.add_task(f"🔄 Fetching {base_branch} branch...", total=1)
        run_git_command(f"git fetch origin {base_branch}")
        progress.update(task1, advance=1)

        task2 = progress.add_task(f"📊 Analyzing changes vs {base_branch}...", total=1)
        changed_files = run_git_command(f"git diff --name-only origin/{base_branch}")
        progress.update(task2, advance=1)

    if not changed_files:
        console.print("[yellow]ℹ️ No changes detected.[/yellow] [dim]No changelog entries to generate[/dim]")
        return []

    # Extract package names from changed files
    changed_packages = set()
    for file in changed_files.split("\n"):
        if file.startswith("packages/") and "/src" in file:
            package = file.split("/")[1]
            changed_packages.add(package)

    # Treat changes in `typescript` directory as `ragbits-chat` package
    if any("typescript/" in file for file in changed_files.split("\n")):
        changed_packages.add("ragbits-chat")

    return sorted(changed_packages)


def get_ignored_packages(base_branch: str) -> set[str]:
    """Get packages that should be ignored based on commit messages."""
    commit_messages = run_git_command(f"git log --pretty=format:%B origin/{base_branch}..HEAD")
    ignored_packages = set()

    for line in commit_messages.split("\n"):
        match = re.match(r"^Changelog-ignore: (.+)$", line.strip())
        if match:
            ignored_packages.add(match.group(1))

    return ignored_packages


async def generate_changelog_entry(package: str, base_branch: str) -> str | None:
    """Generate changelog entry using Claude."""
    # Get commit messages
    commit_messages = run_git_command(f"git log --pretty=format:'%s' origin/{base_branch}..HEAD")

    # Get package-specific changed files
    changed_files = run_git_command(f"git diff --name-only origin/{base_branch} -- packages/{package}/")
    package_changed_files = "\n".join(changed_files.split("\n")[:10])  # Limit to 10 files

    # Get git diff for the package
    package_diff = run_git_command(f"git diff origin/{base_branch} -- packages/{package}/ | head -50")

    # Create context for Claude
    context = f"""Package: {package}
Base branch: {base_branch}

Recent commit messages:
{commit_messages}

Changed files in this package:
{package_changed_files}

Git diff excerpt:
{package_diff}

Please generate a concise changelog entry for the "## Unreleased" section.
The entry should:
1. Start with a category prefix: "feat:", "fix:", "refactor:", "docs:", "test:", "chore:", etc.
2. Be a single line describing the main change
3. Focus on user-facing changes rather than internal implementation details
4. Do NOT include any bullet points, dashes, asterisks, or other formatting characters
5. Do NOT include markdown formatting

Respond with ONLY the changelog entry text, nothing else. Example format:
feat: add new user authentication system"""

    try:
        process = await asyncio.create_subprocess_exec(
            "claude",
            "-p",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, _ = await process.communicate(input=context.encode())

        if process.returncode == 0:
            changelog_entry = stdout.decode().strip().split("\n")[-1]  # Get last line
            # Clean up any unwanted characters that might prefix the entry
            changelog_entry = re.sub(r"^[-*\s•]+", "", changelog_entry).strip()
            return changelog_entry
        else:
            return None

    except Exception:
        return None


def add_changelog_entry(package: str, entry: str) -> bool:
    """Add entry to package changelog."""
    changelog_path = f"packages/{package}/CHANGELOG.md"

    try:
        with open(changelog_path) as f:
            content = f.read()

        # Add entry after "## Unreleased" line
        updated_content = re.sub(r"(## Unreleased\n)", f"\\1\n- {entry}\n", content)

        with open(changelog_path, "w") as f:
            f.write(updated_content)

        return True

    except Exception as e:
        print_error(f"Error updating changelog for {package}: {e}")
        return False


async def process_package(package: str, base_branch: str, package_data: dict) -> None:
    """Process a package and generate its changelog entry."""
    package_data[package]["status"] = "processing"

    entry = await generate_changelog_entry(package, base_branch)

    if entry:
        package_data[package]["entry"] = entry
        package_data[package]["status"] = "success"
        add_changelog_entry(package, entry)
    else:
        package_data[package]["status"] = "failed"


def initialize_package_data(packages_to_process: list[str], base_branch: str) -> dict:
    """Initialize package data with file counts and status."""
    package_data = {}
    for package in packages_to_process:
        changed_files = run_git_command(f"git diff --name-only origin/{base_branch} -- packages/{package}/")
        file_count = len([f for f in changed_files.split("\n") if f.strip()])
        package_data[package] = {"file_count": file_count, "entry": None, "status": "pending"}
    return package_data


def create_status_table(packages_to_process: list[str], package_data: dict) -> Table:
    """Create updated table with current status."""
    table = Table(box=box.ROUNDED)
    table.add_column("Package", style="cyan", no_wrap=True)
    table.add_column("Changed Files", style="dim", width=15)
    table.add_column("Changelog Entry", style="green", width=60)

    for package in packages_to_process:
        data = package_data[package]

        if data["status"] == "pending":
            status_text = "[yellow]⏳ Generating...[/yellow]"
        elif data["status"] == "processing":
            status_text = "[blue]🔄 Processing...[/blue]"
        elif data["status"] == "success":
            status_text = f"[green]✅ {data['entry']}[/green]"
        else:  # failed
            status_text = "[red]❌ Failed[/red]"

        table.add_row(package, f"{data['file_count']} files", status_text)

    return table


async def process_packages_with_display(packages_to_process: list[str], base_branch: str, package_data: dict) -> None:
    """Process packages with live display updates."""

    async def update_display_periodically(live: Live, stop_event: asyncio.Event) -> None:
        """Update the display periodically while processing."""
        while not stop_event.is_set():
            live.update(create_status_table(packages_to_process, package_data))
            await asyncio.sleep(0.25)  # Update every 250ms

    with Live(create_status_table(packages_to_process, package_data), console=console, refresh_per_second=4) as live:
        stop_event = asyncio.Event()
        display_task = asyncio.create_task(update_display_periodically(live, stop_event))
        await asyncio.gather(*[process_package(package, base_branch, package_data) for package in packages_to_process])
        stop_event.set()
        await display_task
        live.update(create_status_table(packages_to_process, package_data))


def print_summary(packages_to_process: list[str], package_data: dict) -> None:
    """Print the final summary."""
    success_count = sum(1 for package in packages_to_process if package_data[package]["status"] == "success")
    console.print()

    if success_count == len(packages_to_process):
        summary = (
            f"[bold green]🎉 All Done![/bold green] [dim]Successfully generated {success_count} changelog entries[/dim]"
        )
    else:
        failed_count = len(packages_to_process) - success_count
        summary = (
            "[bold yellow]⚠️ Partial Success[/bold yellow] "
            f"[dim]Generated {success_count} entries, {failed_count} failed[/dim]"
        )

    console.print(summary)


async def main() -> None:
    """Generate changelog entries for changed packages."""
    base_branch = sys.argv[1] if len(sys.argv) > 1 else "develop"

    console.print(
        f"[bold cyan]🚀 Changelog Generator[/bold cyan] [dim]Comparing against [bold]{base_branch}[/bold] branch[/dim]"
    )

    # Get changed packages
    changed_packages = get_changed_packages(base_branch)
    if not changed_packages:
        console.print("[yellow]ℹ️ No package changes detected[/yellow] [dim]No changelog entries to generate[/dim]")
        return

    # Get ignored packages and filter
    ignored_packages = get_ignored_packages(base_branch)
    packages_to_process = [pkg for pkg in changed_packages if pkg not in ignored_packages]

    if not packages_to_process:
        console.print("[yellow]ℹ️ All packages are ignored[/yellow] [dim]No changelog entries to generate[/dim]")
        return

    # Process packages
    package_data = initialize_package_data(packages_to_process, base_branch)
    await process_packages_with_display(packages_to_process, base_branch, package_data)
    print_summary(packages_to_process, package_data)


if __name__ == "__main__":
    asyncio.run(main())
