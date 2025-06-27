import sys
from pathlib import Path

GIT_URL_TEMPLATE = "git+https://github.com/deepsense-ai/ragbits.git@{branch}#subdirectory=packages/{package}"


def patch_dependencies(file: Path, branch_to_patch: str) -> None:
    """
    Reads the content of the file, applies the patch to dependencies,
    and writes the patched content back to the file.

    Args:
        file: Path to the file to patch.
        branch_to_patch: The branch to patch the dependencies to.
    """
    in_script_block = False
    output_lines = []

    with file.open("r") as lines:
        for line in lines:
            if line.startswith("# /// script"):
                in_script_block = True
                output_lines.append(line)
                continue

            if in_script_block and line.startswith("# ///"):
                in_script_block = False
                output_lines.append(line)
                continue

            if in_script_block and "ragbits" in line:
                start = line.find('"') + 1
                end = line.find('"', start)
                pkg = line[start:end]
                pkg_base = pkg.split("[")[0]
                git_url = GIT_URL_TEMPLATE.format(branch=branch_to_patch, package=pkg_base)
                patched_pkg = f'# "{pkg} @ {git_url}",\n'
                output_lines.append(patched_pkg)
            else:
                output_lines.append(line)

    file.write_text("".join(output_lines))


if __name__ == "__main__":
    file = Path(sys.argv[1])
    branch_to_patch = sys.argv[2] if len(sys.argv) > 2 else "main"  # noqa PLR2004
    patch_dependencies(file, branch_to_patch)
