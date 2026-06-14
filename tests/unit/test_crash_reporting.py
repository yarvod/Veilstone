from __future__ import annotations

from pathlib import Path

import pytest

from voxel_sandbox.app.crash_reporting import write_crash_log


def test_write_crash_log_uses_application_data_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("VEILSTONE_DATA_DIR", str(tmp_path))
    error = RuntimeError("packaged failure")

    path = write_crash_log(type(error), error, error.__traceback__)

    assert path == tmp_path / "logs/crash.log"
    assert "RuntimeError: packaged failure" in path.read_text(encoding="utf-8")
