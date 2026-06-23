from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import sys
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path

from voxel_sandbox.app.paths import updates_root


class UpdateInstallError(RuntimeError):
    pass


@dataclass(frozen=True)
class UpdateInstallPlan:
    script_path: Path
    archive_path: Path
    payload_root: Path
    target_root: Path
    backup_root: Path


def current_install_root(
    *,
    executable: Path | None = None,
    platform: str | None = None,
    frozen: bool | None = None,
) -> Path:
    is_frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    if not is_frozen and executable is None:
        raise UpdateInstallError("Update install requires a packaged app.")

    current_platform = sys.platform if platform is None else platform
    exe = Path(sys.executable if executable is None else executable).resolve()
    if current_platform == "darwin":
        for parent in exe.parents:
            if parent.suffix == ".app":
                return parent
        raise UpdateInstallError("Could not locate macOS .app bundle.")
    return exe.parent


def prepare_update_install(
    archive_path: Path,
    *,
    target_root: Path | None = None,
    staging_root: Path | None = None,
    platform: str | None = None,
    pid: int | None = None,
) -> UpdateInstallPlan:
    archive = archive_path.resolve()
    if not archive.is_file():
        raise UpdateInstallError(f"Update archive does not exist: {archive}")

    current_platform = sys.platform if platform is None else platform
    target = (
        current_install_root(platform=current_platform)
        if target_root is None
        else target_root.resolve()
    )
    if not target.exists():
        raise UpdateInstallError(f"Current install root does not exist: {target}")

    root = staging_root or updates_root()
    prepared_root = root / "prepared" / _safe_stem(archive.stem)
    extract_root = prepared_root / "extract"
    scripts_root = prepared_root / "scripts"
    if prepared_root.exists():
        shutil.rmtree(prepared_root)
    extract_root.mkdir(parents=True, exist_ok=True)
    scripts_root.mkdir(parents=True, exist_ok=True)

    _extract_zip_safe(archive, extract_root)
    payload = _find_payload_root(extract_root, platform=current_platform)
    backup = target.with_name(f"{target.name}.backup.{int(time.time())}")
    script = _write_installer_script(
        scripts_root,
        payload_root=payload,
        target_root=target,
        backup_root=backup,
        platform=current_platform,
        pid=os.getpid() if pid is None else pid,
    )
    return UpdateInstallPlan(
        script_path=script,
        archive_path=archive,
        payload_root=payload,
        target_root=target,
        backup_root=backup,
    )


def launch_update_installer(plan: UpdateInstallPlan, *, platform: str | None = None) -> None:
    current_platform = sys.platform if platform is None else platform
    if current_platform == "win32":
        subprocess.Popen(
            ["cmd", "/c", "start", "", str(plan.script_path)],
            close_fds=True,
        )
        return
    subprocess.Popen([str(plan.script_path)], close_fds=True)


def _safe_stem(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")
    return safe or "update"


def _extract_zip_safe(archive: Path, destination: Path) -> None:
    root = destination.resolve()
    with zipfile.ZipFile(archive) as zip_file:
        for info in zip_file.infolist():
            target = (root / info.filename).resolve()
            if root != target and root not in target.parents:
                raise UpdateInstallError(f"Unsafe archive member: {info.filename}")
        zip_file.extractall(root)


def _find_payload_root(extract_root: Path, *, platform: str) -> Path:
    if platform == "darwin":
        apps = sorted(extract_root.glob("*.app"))
        if apps:
            return apps[0]
    folders = [path for path in extract_root.iterdir() if path.is_dir()]
    for folder in folders:
        if folder.name == "Veilstone":
            return folder
    if len(folders) == 1:
        return folders[0]
    raise UpdateInstallError("Could not find update payload in archive.")


def _write_installer_script(
    scripts_root: Path,
    *,
    payload_root: Path,
    target_root: Path,
    backup_root: Path,
    platform: str,
    pid: int,
) -> Path:
    if platform == "win32":
        script_path = scripts_root / "apply_update.bat"
        script_path.write_text(
            _windows_script(payload_root, target_root, backup_root, pid),
            encoding="utf-8",
            newline="\r\n",
        )
        return script_path

    script_path = scripts_root / "apply_update.sh"
    script_path.write_text(
        _posix_script(payload_root, target_root, backup_root, pid),
        encoding="utf-8",
    )
    mode = script_path.stat().st_mode
    script_path.chmod(mode | stat.S_IXUSR)
    return script_path


def _posix_script(payload_root: Path, target_root: Path, backup_root: Path, pid: int) -> str:
    return f"""#!/usr/bin/env bash
set -euo pipefail

APP_PID={pid}
PAYLOAD={_sh_quote(payload_root)}
TARGET={_sh_quote(target_root)}
BACKUP={_sh_quote(backup_root)}

while kill -0 "$APP_PID" 2>/dev/null; do
  sleep 0.5
done

rm -rf "$BACKUP"
if [ -e "$TARGET" ]; then
  mv "$TARGET" "$BACKUP"
fi
mv "$PAYLOAD" "$TARGET"
rm -rf "$BACKUP"

if [[ "$TARGET" == *.app ]]; then
  open "$TARGET"
elif [ -x "$TARGET/Veilstone" ]; then
  "$TARGET/Veilstone" >/dev/null 2>&1 &
fi
"""


def _windows_script(payload_root: Path, target_root: Path, backup_root: Path, pid: int) -> str:
    return f"""@echo off
setlocal
set "APP_PID={pid}"
set "PAYLOAD={payload_root}"
set "TARGET={target_root}"
set "BACKUP={backup_root}"

:wait
tasklist /FI "PID eq %APP_PID%" | find "%APP_PID%" >nul
if %ERRORLEVEL%==0 (
  timeout /t 1 /nobreak >nul
  goto wait
)

if exist "%BACKUP%" rmdir /s /q "%BACKUP%"
if exist "%TARGET%" move "%TARGET%" "%BACKUP%" >nul
move "%PAYLOAD%" "%TARGET%" >nul
if exist "%BACKUP%" rmdir /s /q "%BACKUP%"

if exist "%TARGET%\\Veilstone.exe" start "" "%TARGET%\\Veilstone.exe"
endlocal
"""


def _sh_quote(path: Path) -> str:
    return "'" + str(path).replace("'", "'\"'\"'") + "'"
