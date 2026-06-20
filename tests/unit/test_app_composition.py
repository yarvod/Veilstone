from __future__ import annotations

from pathlib import Path

from voxel_sandbox.app.composition import (
    UserSettingsStore,
    build_app_runtime,
    build_local_world_runtime,
    build_world_runtime,
    build_world_scene_dependencies,
)
from voxel_sandbox.app.settings import AppSettings
from voxel_sandbox.audio.backend import NullAudioBackend
from voxel_sandbox.audio.bus import AudioBus
from voxel_sandbox.audio.director import AudioDirector
from voxel_sandbox.domain.items import ItemRegistry
from voxel_sandbox.engine.ecs import EntitySimulation
from voxel_sandbox.engine.events import EventBus
from voxel_sandbox.engine.generation import ChunkStreamer, TerrainGenerator
from voxel_sandbox.engine.physics import PlayerController
from voxel_sandbox.infrastructure.storage import WorldStorage


def test_build_app_runtime_composes_app_level_dependencies(tmp_path: Path) -> None:
    settings = AppSettings()

    runtime = build_app_runtime(
        settings,
        data_root=tmp_path,
        settings_store=UserSettingsStore(tmp_path / "settings.toml"),
        audio_backend=NullAudioBackend(),
    )

    assert runtime.settings is settings
    assert runtime.data_root == tmp_path
    assert isinstance(runtime.event_bus, EventBus)
    assert isinstance(runtime.audio, AudioBus)
    assert isinstance(runtime.audio_director, AudioDirector)
    assert isinstance(runtime.content_registries.item_registry, ItemRegistry)
    assert runtime.content_registries.item_registry.by_key("dirt").block_id == 2


def test_user_settings_store_round_trips_user_settings(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.toml"
    store = UserSettingsStore(settings_path)
    settings = AppSettings()

    store.save(settings)

    assert settings_path.exists()
    assert store.load().graphics.resource_pack_path == settings.graphics.resource_pack_path


def test_build_world_runtime_records_active_world_dependencies() -> None:
    storage = object()
    block_registry = object()
    generation = object()
    streaming = object()
    player_state = object()
    entity_world = object()
    renderer = object()

    runtime = build_world_runtime(
        storage=storage,
        block_registry=block_registry,
        generation=generation,
        streaming=streaming,
        player_state=player_state,
        entity_simulation=entity_world,
        entity_world=entity_world,
        renderer=renderer,
    )

    assert runtime.storage is storage
    assert runtime.block_registry is block_registry
    assert runtime.generation is generation
    assert runtime.streaming is streaming
    assert runtime.player_state is player_state
    assert runtime.entity_simulation is entity_world
    assert runtime.entity_world is entity_world
    assert runtime.renderer is renderer


def test_build_local_world_runtime_creates_player_and_entity_simulation() -> None:
    runtime = build_local_world_runtime(
        spawn_position=(1.0, 2.0, 3.0),
        entity_seed=42,
    )

    assert isinstance(runtime.player_state, PlayerController)
    assert (runtime.player_state.x, runtime.player_state.y, runtime.player_state.z) == (
        1.0,
        2.0,
        3.0,
    )
    assert isinstance(runtime.entity_simulation, EntitySimulation)
    assert runtime.entity_world is runtime.entity_simulation.world


def test_build_world_scene_dependencies_composes_world_ownership(tmp_path: Path) -> None:
    dependencies = build_world_scene_dependencies(
        seed="composition-seed",
        save_root=tmp_path / "world",
        render_distance=0,
        generation_workers=1,
        generation_backend="thread",
    )

    assert isinstance(dependencies.storage, WorldStorage)
    assert dependencies.storage.load_metadata() is not None
    assert dependencies.block_registry.by_key("dirt").id == 2
    assert isinstance(dependencies.generation, TerrainGenerator)
    assert isinstance(dependencies.streaming, ChunkStreamer)
    assert dependencies.world_name == "Development World"
    assert dependencies.seed_text == "composition-seed"
