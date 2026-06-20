"""Manual composition root types for Veilstone runtime ownership.

GameWindow still owns most wiring today. This module is the migration target:
small PRs should move construction here, then pass ready runtimes outward.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol, cast

from voxel_sandbox.app.paths import application_data_root, resource_path
from voxel_sandbox.app.settings import AppSettings, load_settings, save_user_settings
from voxel_sandbox.audio.backend import AudioBackend
from voxel_sandbox.audio.bus import AudioBus
from voxel_sandbox.audio.director import AudioDirector
from voxel_sandbox.audio.runtime import create_audio_bus
from voxel_sandbox.domain.biomes import load_biome_registry_from_toml
from voxel_sandbox.domain.blocks import load_block_registry_from_toml
from voxel_sandbox.domain.items import ItemRegistry, load_item_registry_from_toml
from voxel_sandbox.engine.ecs import EntitySimulation
from voxel_sandbox.engine.events import EventBus
from voxel_sandbox.engine.generation import ChunkStreamer, TerrainGenerator, WorldSeed
from voxel_sandbox.engine.physics import PlayerController
from voxel_sandbox.infrastructure.storage import WorldStorage


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
    entity_simulation: Any | None = None
    entity_world: Any | None = None
    simulation_systems: tuple[Any, ...] = ()
    renderer: Any | None = None


@dataclass(frozen=True, slots=True)
class WorldSceneDependencies:
    """World data dependencies consumed by the current scene renderer."""

    storage: WorldStorage
    block_registry: Any
    generation: TerrainGenerator
    streaming: ChunkStreamer
    world_name: str
    seed_text: str


def build_world_runtime(
    *,
    storage: Any | None = None,
    block_registry: Any | None = None,
    generation: Any | None = None,
    streaming: Any | None = None,
    player_state: Any | None = None,
    entity_simulation: Any | None = None,
    entity_world: Any | None = None,
    simulation_systems: tuple[Any, ...] = (),
    renderer: Any | None = None,
) -> WorldRuntime:
    """Record active-world dependencies behind a single runtime context."""

    return WorldRuntime(
        storage=storage,
        block_registry=block_registry,
        generation=generation,
        streaming=streaming,
        player_state=player_state,
        entity_simulation=entity_simulation,
        entity_world=entity_world,
        simulation_systems=simulation_systems,
        renderer=renderer,
    )


def build_local_world_runtime(
    *,
    spawn_position: tuple[float, float, float],
    entity_seed: int,
    storage: Any | None = None,
    block_registry: Any | None = None,
    generation: Any | None = None,
    streaming: Any | None = None,
    renderer: Any | None = None,
) -> WorldRuntime:
    """Build local active-world simulation state without owning render setup."""

    spawn_x, spawn_y, spawn_z = spawn_position
    player = PlayerController(x=spawn_x, y=spawn_y, z=spawn_z)
    entities = EntitySimulation(seed=entity_seed)
    return build_world_runtime(
        storage=storage,
        block_registry=block_registry,
        generation=generation,
        streaming=streaming,
        player_state=player,
        entity_simulation=entities,
        entity_world=entities.world,
        renderer=renderer,
    )


def build_world_scene_dependencies(
    *,
    seed: str,
    save_root: Path,
    render_distance: int,
    generation_workers: int,
    generation_backend: str,
) -> WorldSceneDependencies:
    """Build active-world storage, generation, and streaming dependencies."""

    storage = WorldStorage(save_root)
    metadata = storage.load_metadata()
    active_seed = metadata.seed if metadata is not None else seed
    world_name = metadata.name if metadata is not None else "Development World"
    if metadata is None:
        storage.ensure_world(name=world_name, seed=active_seed)

    block_registry = load_block_registry_from_toml(resource_path("data/blocks.toml"))
    biome_registry = load_biome_registry_from_toml(resource_path("data/biomes.toml"))
    generator = TerrainGenerator(
        WorldSeed.parse(active_seed),
        block_registry=block_registry,
        biome_registry=biome_registry,
    )
    streamer = ChunkStreamer(
        generator,
        render_distance=render_distance,
        workers=generation_workers,
        backend=cast(Literal["thread", "process"], generation_backend),
        prepare_lighting=True,
        storage=storage,
    )
    return WorldSceneDependencies(
        storage=storage,
        block_registry=block_registry,
        generation=generator,
        streaming=streamer,
        world_name=world_name,
        seed_text=active_seed,
    )


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
