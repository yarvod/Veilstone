from __future__ import annotations

from collections import deque
from collections.abc import Mapping

from voxel_sandbox.audio.backend import AudioBackend
from voxel_sandbox.audio.events import AudioEvent, AudioEventKind, VolumeGroup
from voxel_sandbox.audio.registry import AudioRegistry


class AudioBus:
    def __init__(
        self, backend: AudioBackend, registry: AudioRegistry, volumes: Mapping[VolumeGroup, float]
    ) -> None:
        self.backend = backend
        self.registry = registry
        self.volumes = dict(volumes)
        self._events: deque[AudioEvent] = deque()
        self.backend.set_volumes(self.volumes)

    def emit(self, event: AudioEvent) -> None:
        self._events.append(event)

    def update(self, listener: tuple[float, float, float]) -> None:
        self.backend.set_listener(listener)
        while self._events:
            event = self._events.popleft()
            if event.kind is AudioEventKind.STOP_MUSIC:
                self.backend.stop_group(VolumeGroup.MUSIC)
                continue
            if event.kind is AudioEventKind.STOP_AMBIENCE:
                self.backend.stop_group(VolumeGroup.AMBIENCE)
                continue
            resource = self.registry.get(event.key)
            master = self.volumes.get(VolumeGroup.MASTER, 1.0)
            group = self.volumes.get(resource.group, 1.0)
            self.backend.play(resource, master * group * resource.gain, event.position)

    def set_volumes(self, volumes: Mapping[VolumeGroup, float]) -> None:
        self.volumes = dict(volumes)
        self.backend.set_volumes(self.volumes)

    def close(self) -> None:
        self.backend.close()
