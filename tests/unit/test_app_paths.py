from __future__ import annotations

from pathlib import Path

import pytest

from voxel_sandbox.app.paths import (
    application_data_root,
    crash_log_path,
    default_server_world_path,
    resource_packs_root,
    resource_path,
    updates_root,
    user_settings_path,
)


def test_development_paths_stay_inside_ignored_saves(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VEILSTONE_DATA_DIR", raising=False)
    assert application_data_root() == Path("saves")
    assert user_settings_path() == Path("saves/settings.toml")
    assert crash_log_path() == Path("saves/logs/crash.log")
    assert updates_root() == Path("saves/updates")
    assert resource_packs_root() == Path("saves/resource_packs")
    assert default_server_world_path() == Path("saves/server_world")
    assert resource_path("config/settings.toml").is_file()


def test_data_directory_can_be_overridden(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("VEILSTONE_DATA_DIR", str(tmp_path))
    assert application_data_root() == tmp_path
    assert updates_root() == tmp_path / "updates"
    assert resource_packs_root() == tmp_path / "resource_packs"
    assert default_server_world_path() == tmp_path / "server_world"


def test_frozen_resource_path_uses_pyinstaller_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("sys.frozen", True, raising=False)
    monkeypatch.setattr("sys._MEIPASS", str(tmp_path), raising=False)
    assert resource_path("config/recipes.toml") == tmp_path / "config/recipes.toml"
