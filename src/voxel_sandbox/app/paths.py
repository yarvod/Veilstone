from __future__ import annotations

import os
import sys
from pathlib import Path


def resource_path(relative: str | Path) -> Path:
    if getattr(sys, "frozen", False):
        root = Path(vars(sys)["_MEIPASS"])
        return root / relative
    project_resource = Path(__file__).parents[3] / relative
    if project_resource.exists():
        return project_resource
    return Path(__file__).parents[1] / "resources" / relative


def application_data_root() -> Path:
    override = os.environ.get("VEILSTONE_DATA_DIR")
    if override:
        return Path(override)
    if not getattr(sys, "frozen", False):
        return Path("saves")
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/Veilstone"
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home())) / "Veilstone"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "veilstone"


def user_settings_path() -> Path:
    return application_data_root() / "settings.toml"


def crash_log_path() -> Path:
    return application_data_root() / "logs/crash.log"


def updates_root() -> Path:
    return application_data_root() / "updates"


def resource_packs_root() -> Path:
    return application_data_root() / "resource_packs"


def default_server_world_path() -> Path:
    return application_data_root() / "server_world"
