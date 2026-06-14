from __future__ import annotations

from voxel_sandbox.app.paths import resource_path
from voxel_sandbox.app.settings import AudioSettings
from voxel_sandbox.audio import (
    AudioDirector,
    AudioEvent,
    AudioEventKind,
    NullAudioBackend,
    VolumeGroup,
)
from voxel_sandbox.audio.runtime import create_audio_bus, create_server_audio_bus


def test_audio_bus_routes_positional_effect_with_group_volumes() -> None:
    backend = NullAudioBackend()
    bus = create_audio_bus(AudioSettings(master=0.5, effects=0.4), backend)

    bus.emit(AudioEvent(AudioEventKind.SOUND, "block.stone", (1.0, 2.0, 3.0)))
    bus.update((4.0, 5.0, 6.0))

    resource, volume, position = backend.played[-1]
    assert resource.key == "block.stone"
    assert volume == 0.2
    assert position == (1.0, 2.0, 3.0)
    assert backend.listener == (4.0, 5.0, 6.0)


def test_director_changes_music_and_biome_ambience_once() -> None:
    backend = NullAudioBackend()
    bus = create_audio_bus(AudioSettings(), backend)
    director = AudioDirector(bus)

    director.set_game_state("exploration")
    director.set_game_state("exploration")
    director.set_biome("surface")
    director.set_biome("cave")
    bus.update((0.0, 0.0, 0.0))

    assert [entry[0].key for entry in backend.played] == [
        "music.exploration",
        "ambience.surface",
        "ambience.cave",
    ]
    assert backend.stopped.count(VolumeGroup.AMBIENCE) == 0


def test_server_audio_uses_null_backend() -> None:
    bus = create_server_audio_bus(AudioSettings())

    assert isinstance(bus.backend, NullAudioBackend)
    bus.emit(AudioEvent(AudioEventKind.SOUND, "mob.hit"))
    bus.update((0.0, 0.0, 0.0))
    assert len(bus.backend.played) == 1


def test_audio_registry_and_original_assets_exist() -> None:
    assert resource_path("config/audio.toml").is_file()
    assert resource_path("assets/audio/ambience_surface.wav").is_file()
