"""Manual composition root types for Veilstone runtime ownership.

GameWindow still owns most wiring today. This module is the migration target:
small PRs should move construction here, then pass ready runtimes outward.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from voxel_sandbox.app.paths import application_data_root, resource_path
from voxel_sandbox.app.settings import AppSettings, load_settings, save_user_settings
from voxel_sandbox.audio.backend import AudioBackend
from voxel_sandbox.audio.bus import AudioBus
from voxel_sandbox.audio.director import AudioDirector
from voxel_sandbox.audio.runtime import create_audio_bus
from voxel_sandbox.domain.items import ItemRegistry, load_item_registry_from_toml
from voxel_sandbox.engine.events import EventBus


class SettingsStorePort(Protocol):
    """Loads and saves user-facing settings."""

    def load(self) -> AppSettings: ...

    def save(self, settings: AppSettings) -> None: ...


@dataclass(frozen=True, slots=True)
class UserSettingsStore:
    """File-backed settings store used by the default application runtime."""

    path: Path | None = None

    def load(self) -> AppSettings:
        return load_settings(self.path)

    def save(self, settings: AppSettings) -> None:
        save_user_settings(settings, self.path)


@dataclass(frozen=True, slots=True)
class ContentRegistries:
    """Application-level registries shared across worlds."""

    item_registry: ItemRegistry


@dataclass(slots=True)
class AppRuntime:
    """Application-lifetime dependencies shared across worlds."""

    settings: AppSettings
    data_root: Path
    event_bus: EventBus
    audio: AudioBus
    audio_director: AudioDirector
    content_registries: ContentRegistries
    settings_store: SettingsStorePort
    texture_packs: Any | None = None


@dataclass(slots=True)
class WorldRuntime:
    """Active-world dependencies that are replaced when switching worlds."""

    storage: Any | None = None
    block_registry: Any | None = None
    generation: Any | None = None
    streaming: Any | None = None
    player_state: Any | None = None
    entity_world: Any | None = None
    simulation_systems: tuple[Any, ...] = ()
    renderer: Any | None = None


def build_app_runtime(
    settings: AppSettings,
    *,
    data_root: Path | None = None,
    settings_store: SettingsStorePort | None = None,
    audio_backend: AudioBackend | None = None,
) -> AppRuntime:
    """Build app-lifetime dependencies without constructing a window or world."""

    audio = create_audio_bus(settings.audio, backend=audio_backend)
    return AppRuntime(
        settings=settings,
        data_root=data_root or application_data_root(),
        event_bus=EventBus(),
        audio=audio,
        audio_director=AudioDirector(audio),
        content_registries=ContentRegistries(
            item_registry=load_item_registry_from_toml(resource_path("data/items.toml")),
        ),
        settings_store=settings_store or UserSettingsStore(),
    )
