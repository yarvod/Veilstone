from __future__ import annotations

import argparse
import re
from pathlib import Path

from packaging.version import InvalidVersion, Version

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
VERSION_FILE = ROOT / "src/voxel_sandbox/version.py"
REPO_SLUG = "yarvod/Veilstone"
TAG_PATTERN = re.compile(r"^v(?P<version>\d+\.\d+\.\d+(?:[-_.+A-Za-z0-9]*)?)$")


def main() -> int:
    parser = argparse.ArgumentParser(description="Update Veilstone release version files.")
    parser.add_argument(
        "--check-current",
        action="store_true",
        help="Validate that current version files already match the release tag.",
    )
    parser.add_argument("tag", help="Release tag, for example v0.2.0")
    args = parser.parse_args()
    tag = str(args.tag).strip()
    version = version_from_tag(tag)
    if args.check_current:
        check_current_version(version, tag)
        return 0
    update_pyproject(version)
    update_version_file(version, tag)
    return 0


def version_from_tag(tag: str) -> str:
    match = TAG_PATTERN.fullmatch(tag)
    if not match:
        raise SystemExit(f"Release tag must look like v0.2.0 or v0.2.0-beta1, got {tag!r}")
    raw_version = match.group("version")
    try:
        return str(Version(raw_version))
    except InvalidVersion as error:
        raise SystemExit(f"Release tag version must be PEP 440 compatible, got {tag!r}") from error


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


def check_current_version(version: str, tag: str) -> None:
    pyproject_text = PYPROJECT.read_text(encoding="utf-8")
    pyproject_match = re.search(r'(?m)^version = "([^"]+)"$', pyproject_text)
    if not pyproject_match:
        raise SystemExit("Could not find project.version in pyproject.toml")
    current_version = pyproject_match.group(1)
    if current_version != version:
        raise SystemExit(f"pyproject.toml version is {current_version!r}, expected {version!r}")

    version_text = VERSION_FILE.read_text(encoding="utf-8")
    version_match = re.search(r'(?m)^__version__ = "([^"]+)"$', version_text)
    tag_match = re.search(r'(?m)^RELEASE_TAG = "([^"]+)"$', version_text)
    if not version_match or not tag_match:
        raise SystemExit("Could not find __version__ or RELEASE_TAG in version.py")
    if version_match.group(1) != version:
        raise SystemExit(
            f"version.py __version__ is {version_match.group(1)!r}, expected {version!r}"
        )
    if tag_match.group(1) != tag:
        raise SystemExit(f"version.py RELEASE_TAG is {tag_match.group(1)!r}, expected {tag!r}")


if __name__ == "__main__":
    raise SystemExit(main())
