from __future__ import annotations

from pathlib import Path

import pytest

from voxel_sandbox.app.package_verification import missing_package_resources, verify_package


def test_development_package_resources_are_present() -> None:
    assert missing_package_resources() == ()


def test_package_verification_writes_user_settings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("VEILSTONE_DATA_DIR", str(tmp_path))

    assert verify_package() == 0
    assert (tmp_path / "settings.toml").is_file()
