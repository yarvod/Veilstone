from __future__ import annotations

from voxel_sandbox.audio.bus import AudioBus
from voxel_sandbox.audio.events import AudioEvent, AudioEventKind


class AudioDirector:
    def __init__(self, bus: AudioBus) -> None:
        self.bus = bus
        self.music_state = ""
        self.biome = ""

    def set_game_state(self, state: str) -> None:
        if state == self.music_state:
            return
        self.music_state = state
        track = {
            "menu": "music.menu",
            "exploration": "music.exploration",
            "night": "music.night",
        }.get(state)
        if track is None:
            self.bus.emit(AudioEvent(AudioEventKind.STOP_MUSIC))
        else:
            self.bus.emit(AudioEvent(AudioEventKind.MUSIC, track))

    def set_biome(self, biome: str) -> None:
        if biome == self.biome:
            return
        self.biome = biome
        key = {"surface": "ambience.surface", "cave": "ambience.cave"}.get(biome)
        if key is None:
            self.bus.emit(AudioEvent(AudioEventKind.STOP_AMBIENCE))
        else:
            self.bus.emit(AudioEvent(AudioEventKind.AMBIENCE, key))
