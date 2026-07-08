from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from voxel_sandbox.app.paths import resource_path, user_settings_path


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
class DevelopmentSettings:
    shader_hot_reload: bool = True
    profile_frame: bool = False
    disable_hud: bool = False
    render_local_player_model: bool = False


@dataclass(frozen=True, slots=True)
class ControlsSettings:
    forward: str = "W"
    backward: str = "S"
    left: str = "A"
    right: str = "D"
    jump: str = "SPACE"


@dataclass(frozen=True, slots=True)
class WorldSettings:
    seed: str = "veilstone-dev"
    render_distance: int = 2
    generation_workers: int = 2
    generation_backend: str = "process"
    chunk_uploads_per_frame: int = 1
    meshing_workers: int = 2
    meshing_backend: str = "process"
    mesh_uploads_per_frame: int = 2


@dataclass(frozen=True, slots=True)
class GameplaySettings:
    difficulty: str = "normal"
    hostile_spawn_light_limit: int = 7

    def __post_init__(self) -> None:
        if self.difficulty not in {"peaceful", "normal"}:
            raise ValueError("Gameplay difficulty must be peaceful or normal")
        if not 0 <= self.hostile_spawn_light_limit <= 15:
            raise ValueError("Hostile spawn light limit must be between 0 and 15")


@dataclass(frozen=True, slots=True)
class GraphicsSettings:
    greedy_meshing: bool = True
    smooth_lighting: bool = True
    ambient_occlusion: bool = True
    fog: bool = True
    fog_start: float = 24.0
    fog_end: float = 56.0
    day_cycle_seconds: float = 1200.0
    shadow_quality: str = "medium"
    shadow_bias: float = 0.0015
    clouds: bool = True
    resource_pack_path: str = ""
    material_quality: str = "color-only"


@dataclass(frozen=True, slots=True)
class AudioSettings:
    master: float = 0.8
    effects: float = 0.7
    music: float = 0.35
    ambience: float = 0.42


@dataclass(frozen=True, slots=True)
class AppSettings:
    window: WindowSettings = field(default_factory=WindowSettings)
    camera: CameraSettings = field(default_factory=CameraSettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)
    development: DevelopmentSettings = field(default_factory=DevelopmentSettings)
    world: WorldSettings = field(default_factory=WorldSettings)
    gameplay: GameplaySettings = field(default_factory=GameplaySettings)
    graphics: GraphicsSettings = field(default_factory=GraphicsSettings)
    audio: AudioSettings = field(default_factory=AudioSettings)
    controls: ControlsSettings = field(default_factory=ControlsSettings)


def _section(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key, {})
    if not isinstance(value, dict):
        raise ValueError(f"Configuration section [{key}] must be a table")
    return cast("dict[str, Any]", value)


def load_settings(path: Path | None = None) -> AppSettings:
    config_path = path or resource_path("config/settings.toml")
    if not config_path.exists():
        return AppSettings()

    with config_path.open("rb") as config_file:
        data = tomllib.load(config_file)
    if path is None:
        user_path = user_settings_path()
        if user_path.exists():
            with user_path.open("rb") as user_file:
                user_data = tomllib.load(user_file)
            for section, values in user_data.items():
                if isinstance(values, dict):
                    data.setdefault(section, {}).update(values)

    graphics_data = _section(data, "graphics")
    graphics_data.pop("postprocess", None)
    return AppSettings(
        window=WindowSettings(**_section(data, "window")),
        camera=CameraSettings(**_section(data, "camera")),
        logging=LoggingSettings(**_section(data, "logging")),
        development=DevelopmentSettings(**_section(data, "development")),
        world=WorldSettings(**_section(data, "world")),
        gameplay=GameplaySettings(**_section(data, "gameplay")),
        graphics=GraphicsSettings(**graphics_data),
        audio=AudioSettings(**_section(data, "audio")),
        controls=ControlsSettings(**_section(data, "controls")),
    )


def save_user_settings(settings: AppSettings, path: Path | None = None) -> None:
    target = path or user_settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    content = (
        "[window]\n"
        f"vsync = {str(settings.window.vsync).lower()}\n"
        f"fullscreen = {str(settings.window.fullscreen).lower()}\n\n"
        "[camera]\n"
        f"field_of_view = {settings.camera.field_of_view}\n"
        f"mouse_sensitivity = {settings.camera.mouse_sensitivity}\n\n"
        "[graphics]\n"
        f'shadow_quality = "{settings.graphics.shadow_quality}"\n'
        f"clouds = {str(settings.graphics.clouds).lower()}\n"
        f"fog = {str(settings.graphics.fog).lower()}\n"
        f'material_quality = "{settings.graphics.material_quality}"\n'
        "\n[world]\n"
        f'seed = "{settings.world.seed}"\n'
        f"render_distance = {settings.world.render_distance}\n"
        f"generation_workers = {settings.world.generation_workers}\n"
        f'generation_backend = "{settings.world.generation_backend}"\n'
        f"chunk_uploads_per_frame = {settings.world.chunk_uploads_per_frame}\n"
        f"meshing_workers = {settings.world.meshing_workers}\n"
        f'meshing_backend = "{settings.world.meshing_backend}"\n'
        f"mesh_uploads_per_frame = {settings.world.mesh_uploads_per_frame}\n"
        "\n[gameplay]\n"
        f'difficulty = "{settings.gameplay.difficulty}"\n'
        f"hostile_spawn_light_limit = {settings.gameplay.hostile_spawn_light_limit}\n"
        "\n[audio]\n"
        f"master = {settings.audio.master}\n"
        f"effects = {settings.audio.effects}\n"
        f"music = {settings.audio.music}\n"
        f"ambience = {settings.audio.ambience}\n"
        "\n[controls]\n"
        f'forward = "{settings.controls.forward}"\n'
        f'backward = "{settings.controls.backward}"\n'
        f'left = "{settings.controls.left}"\n'
        f'right = "{settings.controls.right}"\n'
        f'jump = "{settings.controls.jump}"\n'
    )
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(target)
