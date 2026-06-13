from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast


@dataclass(frozen=True, slots=True)
class WindowSettings:
    title: str = "Veilstone"
    width: int = 1280
    height: int = 720
    vsync: bool = True
    fullscreen: bool = False


@dataclass(frozen=True, slots=True)
class CameraSettings:
    field_of_view: float = 70.0
    movement_speed: float = 8.0
    mouse_sensitivity: float = 0.12


@dataclass(frozen=True, slots=True)
class LoggingSettings:
    level: str = "INFO"


@dataclass(frozen=True, slots=True)
class AppSettings:
    window: WindowSettings = WindowSettings()
    camera: CameraSettings = CameraSettings()
    logging: LoggingSettings = LoggingSettings()


def _section(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key, {})
    if not isinstance(value, dict):
        raise ValueError(f"Configuration section [{key}] must be a table")
    return cast("dict[str, Any]", value)


def load_settings(path: Path | None = None) -> AppSettings:
    config_path = path or Path("config/settings.toml")
    if not config_path.exists():
        return AppSettings()

    with config_path.open("rb") as config_file:
        data = tomllib.load(config_file)

    return AppSettings(
        window=WindowSettings(**_section(data, "window")),
        camera=CameraSettings(**_section(data, "camera")),
        logging=LoggingSettings(**_section(data, "logging")),
    )
