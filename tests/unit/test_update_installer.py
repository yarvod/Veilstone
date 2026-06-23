from __future__ import annotations

import stat
import zipfile
from pathlib import Path

import pytest

from voxel_sandbox.app.update_installer import (
    UpdateInstallError,
    current_install_root,
    prepare_update_install,
)


def _write_zip(archive: Path, members: dict[str, bytes]) -> None:
    with zipfile.ZipFile(archive, "w") as zip_file:
        for name, data in members.items():
            zip_file.writestr(name, data)


def test_current_install_root_detects_macos_app_bundle() -> None:
    executable = Path("/Applications/Veilstone.app/Contents/MacOS/Veilstone")

    root = current_install_root(executable=executable, platform="darwin", frozen=True)

    assert root == Path("/Applications/Veilstone.app")


def test_current_install_root_requires_packaged_app_without_explicit_executable() -> None:
    with pytest.raises(UpdateInstallError, match="packaged app"):
        current_install_root(frozen=False)


def test_prepare_update_install_for_macos_bundle(tmp_path: Path) -> None:
    archive = tmp_path / "Veilstone_macOS_arm64_v0_0_2.zip"
    _write_zip(
        archive,
        {
            "Veilstone.app/Contents/MacOS/Veilstone": b"binary",
            "Veilstone.app/Contents/Info.plist": b"plist",
        },
    )
    target = tmp_path / "Installed" / "Veilstone.app"
    target.mkdir(parents=True)

    plan = prepare_update_install(
        archive,
        target_root=target,
        staging_root=tmp_path / "updates",
        platform="darwin",
        pid=123,
    )

    assert plan.payload_root.name == "Veilstone.app"
    assert plan.target_root == target
    assert plan.script_path.name == "apply_update.sh"
    assert plan.script_path.stat().st_mode & stat.S_IXUSR
    script = plan.script_path.read_text(encoding="utf-8")
    assert "APP_PID=123" in script
    assert 'open "$TARGET"' in script


def test_prepare_update_install_for_folder_payload(tmp_path: Path) -> None:
    archive = tmp_path / "Veilstone_Linux_x64_v0_0_2.zip"
    _write_zip(archive, {"Veilstone/Veilstone": b"binary"})
    target = tmp_path / "install" / "Veilstone"
    target.mkdir(parents=True)

    plan = prepare_update_install(
        archive,
        target_root=target,
        staging_root=tmp_path / "updates",
        platform="linux",
        pid=456,
    )

    assert plan.payload_root.name == "Veilstone"
    assert plan.script_path.name == "apply_update.sh"
    assert "APP_PID=456" in plan.script_path.read_text(encoding="utf-8")


def test_prepare_update_install_writes_windows_batch(tmp_path: Path) -> None:
    archive = tmp_path / "Veilstone_Windows_x64_v0_0_2.zip"
    _write_zip(archive, {"Veilstone/Veilstone.exe": b"binary"})
    target = tmp_path / "install" / "Veilstone"
    target.mkdir(parents=True)

    plan = prepare_update_install(
        archive,
        target_root=target,
        staging_root=tmp_path / "updates",
        platform="win32",
        pid=789,
    )

    assert plan.script_path.name == "apply_update.bat"
    script = plan.script_path.read_text(encoding="utf-8")
    assert "APP_PID=789" in script
    assert "Veilstone.exe" in script


def test_prepare_update_install_rejects_zip_slip(tmp_path: Path) -> None:
    archive = tmp_path / "bad.zip"
    _write_zip(archive, {"../escape.txt": b"bad"})
    target = tmp_path / "install"
    target.mkdir()

    with pytest.raises(UpdateInstallError, match="Unsafe archive member"):
        prepare_update_install(
            archive,
            target_root=target,
            staging_root=tmp_path / "updates",
            platform="linux",
        )
