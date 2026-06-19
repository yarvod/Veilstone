from __future__ import annotations

from pathlib import Path

from voxel_sandbox.app.composition import UserSettingsStore, build_app_runtime
from voxel_sandbox.app.settings import AppSettings
from voxel_sandbox.audio.backend import NullAudioBackend
from voxel_sandbox.audio.bus import AudioBus
from voxel_sandbox.audio.director import AudioDirector
from voxel_sandbox.domain.items import ItemRegistry
from voxel_sandbox.engine.events import EventBus


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
