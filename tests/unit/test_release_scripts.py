from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


def _write_executable(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    path.chmod(0o755)


def test_release_sh_replace_tag_moves_existing_remote_tag(tmp_path: Path) -> None:
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("release.sh smoke requires bash")

    log = tmp_path / "commands.log"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    _write_executable(
        fake_bin / "git",
        """#!/usr/bin/env bash
set -euo pipefail
printf 'git' >> "$RELEASE_SCRIPT_LOG"
for arg in "$@"; do
  printf ' <%s>' "$arg" >> "$RELEASE_SCRIPT_LOG"
done
printf '\\n' >> "$RELEASE_SCRIPT_LOG"
if [[ "$1" == "status" && "$2" == "--short" ]]; then
  exit 0
fi
if [[ "$1" == "ls-remote" ]]; then
  printf 'abc123 refs/tags/v0.0.1-beta1\\n'
  exit 0
fi
exit 0
""",
    )
    _write_executable(
        fake_bin / "uv",
        """#!/usr/bin/env bash
set -euo pipefail
printf 'uv' >> "$RELEASE_SCRIPT_LOG"
for arg in "$@"; do
  printf ' <%s>' "$arg" >> "$RELEASE_SCRIPT_LOG"
done
printf '\\n' >> "$RELEASE_SCRIPT_LOG"
exit 0
""",
    )
    env = os.environ | {
        "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
        "RELEASE_SCRIPT_LOG": str(log),
    }

    subprocess.run(
        [bash, "scripts/release.sh", "-t", "v0.0.1-beta1", "--replace-tag"],
        check=True,
        env=env,
    )

    commands = log.read_text(encoding="utf-8")
    assert (
        "uv <run> <python> <scripts/set_release_version.py> <--check-current> <v0.0.1-beta1>"
    ) in commands
    assert ("git <ls-remote> <--exit-code> <--refs> <origin> <refs/tags/v0.0.1-beta1>") in commands
    assert "git <push> <origin> <HEAD>" in commands
    assert "git <tag> <-f> <-a> <v0.0.1-beta1> <-m> <Veilstone v0.0.1-beta1>" in commands
    assert (
        "git <push> <--force-with-lease=refs/tags/v0.0.1-beta1:abc123> "
        "<origin> <refs/tags/v0.0.1-beta1>"
    ) in commands
    assert "uv <lock>" not in commands


def test_release_bat_documents_replace_tag_flow() -> None:
    text = Path("scripts/release.bat").read_text(encoding="utf-8")

    assert "--replace-tag" in text
    assert "--check-current" in text
    assert "git ls-remote --exit-code --refs origin" in text
    assert "git push --force-with-lease=" in text
