from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
VERSION_FILE = ROOT / "src/voxel_sandbox/version.py"
REPO_SLUG = "yarvod/Veilstone"


def main() -> int:
    parser = argparse.ArgumentParser(description="Update Veilstone release version files.")
    parser.add_argument("tag", help="Release tag, for example v0.2.0")
    args = parser.parse_args()
    tag = str(args.tag).strip()
    version = version_from_tag(tag)
    update_pyproject(version)
    update_version_file(version, tag)
    return 0


def version_from_tag(tag: str) -> str:
    if not re.fullmatch(r"v\d+\.\d+\.\d+(?:[A-Za-z0-9_.-]*)?", tag):
        raise SystemExit(f"Release tag must look like v0.2.0, got {tag!r}")
    return tag.removeprefix("v")


def update_pyproject(version: str) -> None:
    text = PYPROJECT.read_text(encoding="utf-8")
    pattern = r'(?m)^version = "[^"]+"$'
    if not re.search(pattern, text):
        raise SystemExit("Could not find project.version in pyproject.toml")
    updated = re.sub(
        pattern,
        f'version = "{version}"',
        text,
        count=1,
    )
    PYPROJECT.write_text(updated, encoding="utf-8")


def update_version_file(version: str, tag: str) -> None:
    VERSION_FILE.write_text(
        "\n".join(
            (
                "from __future__ import annotations",
                "",
                '__all__ = ["RELEASE_TAG", "REPO_SLUG", "__version__"]',
                "",
                f'__version__ = "{version}"',
                f'RELEASE_TAG = "{tag}"',
                f'REPO_SLUG = "{REPO_SLUG}"',
                "",
            )
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
