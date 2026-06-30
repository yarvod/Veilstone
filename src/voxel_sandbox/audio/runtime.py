from __future__ import annotations

from voxel_sandbox.app.paths import resource_path
from voxel_sandbox.app.settings import AudioSettings
from voxel_sandbox.audio.backend import AudioBackend, NullAudioBackend, PygletAudioBackend
from voxel_sandbox.audio.bus import AudioBus
from voxel_sandbox.audio.events import VolumeGroup
from voxel_sandbox.audio.registry import AudioRegistry


def volume_map(settings: AudioSettings) -> dict[VolumeGroup, float]:
    return {
        VolumeGroup.MASTER: settings.master,
        VolumeGroup.EFFECTS: settings.effects,
        VolumeGroup.MUSIC: settings.music,
        VolumeGroup.AMBIENCE: settings.ambience,
    }


def create_audio_bus(
    settings: AudioSettings,
    backend: AudioBackend | None = None,
) -> AudioBus:
    registry = AudioRegistry.from_toml(
        resource_path("config/audio.toml"),
        resource_path("resource_packs/default"),
    )
    return AudioBus(backend or PygletAudioBackend(), registry, volume_map(settings))


def create_server_audio_bus(settings: AudioSettings) -> AudioBus:
    return create_audio_bus(settings, NullAudioBackend())
