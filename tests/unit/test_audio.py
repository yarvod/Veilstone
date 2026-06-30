from __future__ import annotations

import math
import wave
from array import array

from voxel_sandbox.app.paths import resource_path
from voxel_sandbox.app.settings import AudioSettings
from voxel_sandbox.audio import (
    AudioDirector,
    AudioEvent,
    AudioEventKind,
    NullAudioBackend,
    VolumeGroup,
)
from voxel_sandbox.audio.backend import listener_space
from voxel_sandbox.audio.runtime import create_audio_bus, create_server_audio_bus
from voxel_sandbox.audio.steps import footstep_sound_key


def test_audio_bus_routes_positional_effect_with_group_volumes() -> None:
    backend = NullAudioBackend()
    bus = create_audio_bus(AudioSettings(master=0.5, effects=0.4), backend)

    bus.emit(AudioEvent(AudioEventKind.SOUND, "block.stone", (1.0, 2.0, 3.0)))
    bus.update((4.0, 5.0, 6.0))

    resource, volume, position = backend.played[-1]
    assert resource.key == "block.stone"
    assert abs(volume - 0.032) < 1e-9
    assert position == (1.0, 2.0, 3.0)
    assert backend.listener == (4.0, 5.0, 6.0)


def test_footstep_sound_prefers_step_material_keys() -> None:
    assert footstep_sound_key("stone", {"step.stone", "block.stone", "footstep"}) == "step.stone"
    assert footstep_sound_key("glass", {"block.glass", "footstep"}) == "footstep"


def test_step_material_sounds_are_tuned_separately_from_block_actions() -> None:
    bus = create_audio_bus(AudioSettings(), NullAudioBackend())

    assert "step.stone" in bus.registry
    assert "block.stone" in bus.registry
    assert bus.registry.get("step.stone").gain < bus.registry.get("block.stone").gain


def test_player_movement_sounds_are_registered() -> None:
    bus = create_audio_bus(AudioSettings(), NullAudioBackend())

    assert "player.land" in bus.registry
    assert "player.splash" in bus.registry
    assert bus.registry.get("player.land").gain > bus.registry.get("footstep").gain


def test_audio_registry_resolves_default_resource_pack_sounds() -> None:
    bus = create_audio_bus(AudioSettings(), NullAudioBackend())

    assert (
        bus.registry.get("ui.click")
        .paths[0]
        .as_posix()
        .endswith("resource_packs/default/assets/minecraft/sounds/ui/click.wav")
    )
    assert (
        bus.registry.get("mob.passive_hurt")
        .paths[0]
        .as_posix()
        .endswith("resource_packs/default/assets/minecraft/sounds/entity/cow/hurt_1.wav")
    )


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
    bus.emit(AudioEvent(AudioEventKind.SOUND, "mob.hostile_hurt"))
    bus.update((0.0, 0.0, 0.0))
    assert len(bus.backend.played) == 1


def test_audio_registry_and_original_assets_exist() -> None:
    assert resource_path("config/audio.toml").is_file()
    assert resource_path(
        "resource_packs/default/assets/minecraft/sounds/ambient/surface.wav"
    ).is_file()


def test_gameplay_effects_are_normalized_without_clipping() -> None:
    names = (
        "block/stone.wav",
        "block/earth.wav",
        "block/wood.wav",
        "step/footstep.wav",
        "player/hurt.wav",
        "entity/cow/hurt_1.wav",
        "entity/cow/death_1.wav",
        "entity/zombie/hurt_1.wav",
        "entity/zombie/death_1.wav",
    )
    for name in names:
        with wave.open(
            str(resource_path(f"resource_packs/default/assets/minecraft/sounds/{name}")),
            "rb",
        ) as source:
            samples = array("h", source.readframes(source.getnframes()))
        peak = max(abs(sample) for sample in samples) / 32767.0
        rms = math.sqrt(sum(sample * sample for sample in samples) / len(samples)) / 32767.0
        assert 0.25 <= peak <= 0.55
        assert 0.025 <= rms <= 0.30


def test_listener_space_tracks_camera_position_and_orientation() -> None:
    assert listener_space(
        (12.0, 4.0, 5.0),
        (10.0, 4.0, 5.0),
        (0.0, 0.0, -1.0),
        (0.0, 1.0, 0.0),
    ) == (2.0, 0.0, 0.0)
    assert listener_space(
        (10.0, 4.0, 3.0),
        (10.0, 4.0, 5.0),
        (0.0, 0.0, -1.0),
        (0.0, 1.0, 0.0),
    ) == (0.0, 0.0, -2.0)
