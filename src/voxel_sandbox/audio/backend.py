from __future__ import annotations

import logging
import math
import random
from collections.abc import Mapping
from typing import Any, Protocol

from voxel_sandbox.audio.events import VolumeGroup
from voxel_sandbox.audio.registry import AudioResource

LOGGER = logging.getLogger(__name__)


class AudioBackend(Protocol):
    def set_listener(
        self,
        position: tuple[float, float, float],
        forward: tuple[float, float, float],
        up: tuple[float, float, float],
    ) -> None: ...

    def play(
        self, resource: AudioResource, volume: float, position: tuple[float, float, float] | None
    ) -> None: ...

    def stop_group(self, group: VolumeGroup) -> None: ...

    def set_volumes(self, volumes: Mapping[VolumeGroup, float]) -> None: ...

    def close(self) -> None: ...


class NullAudioBackend:
    def __init__(self) -> None:
        self.played: list[tuple[AudioResource, float, tuple[float, float, float] | None]] = []
        self.stopped: list[VolumeGroup] = []
        self.listener = (0.0, 0.0, 0.0)
        self.volumes: dict[VolumeGroup, float] = {}

    def set_listener(
        self,
        position: tuple[float, float, float],
        forward: tuple[float, float, float],
        up: tuple[float, float, float],
    ) -> None:
        self.listener = position

    def play(
        self, resource: AudioResource, volume: float, position: tuple[float, float, float] | None
    ) -> None:
        self.played.append((resource, volume, position))

    def stop_group(self, group: VolumeGroup) -> None:
        self.stopped.append(group)

    def set_volumes(self, volumes: Mapping[VolumeGroup, float]) -> None:
        self.volumes = dict(volumes)

    def close(self) -> None:
        pass


class PygletAudioBackend:
    def __init__(self) -> None:
        import pyglet

        self._pyglet = pyglet
        self._players: list[Any] = []
        self._loops: dict[VolumeGroup, Any] = {}
        self._listener = (0.0, 0.0, 0.0)
        self._forward = (0.0, 0.0, -1.0)
        self._up = (0.0, 1.0, 0.0)

    def set_listener(
        self,
        position: tuple[float, float, float],
        forward: tuple[float, float, float],
        up: tuple[float, float, float],
    ) -> None:
        self._listener = position
        self._forward = _normalized(forward, fallback=(0.0, 0.0, -1.0))
        self._up = _normalized(up, fallback=(0.0, 1.0, 0.0))

    def play(
        self, resource: AudioResource, volume: float, position: tuple[float, float, float] | None
    ) -> None:
        try:
            path = random.choice(resource.paths)
            source = self._pyglet.media.load(str(path), streaming=resource.loop)
            player = self._pyglet.media.Player()
            player.volume = max(0.0, min(volume, 1.0))
            if position is not None:
                player.position = listener_space(
                    position,
                    self._listener,
                    self._forward,
                    self._up,
                )
                player.min_distance = 3.0
                player.max_distance = 36.0
            player.loop = resource.loop
            player.queue(source)
            player.play()
            if resource.loop:
                self.stop_group(resource.group)
                self._loops[resource.group] = player
            else:
                self._players.append(player)
                self._players = [
                    active for active in self._players if getattr(active, "playing", False)
                ]
        except Exception:
            LOGGER.warning("Unable to play audio resource %s", resource.key, exc_info=True)

    def stop_group(self, group: VolumeGroup) -> None:
        player = self._loops.pop(group, None)
        if player is not None:
            player.delete()

    def set_volumes(self, volumes: Mapping[VolumeGroup, float]) -> None:
        del volumes

    def close(self) -> None:
        for player in (*self._players, *self._loops.values()):
            player.delete()
        self._players.clear()
        self._loops.clear()


def listener_space(
    source: tuple[float, float, float],
    listener: tuple[float, float, float],
    forward: tuple[float, float, float],
    up: tuple[float, float, float],
) -> tuple[float, float, float]:
    delta = (
        source[0] - listener[0],
        source[1] - listener[1],
        source[2] - listener[2],
    )
    right = _normalized(_cross(forward, up), fallback=(1.0, 0.0, 0.0))
    corrected_up = _normalized(_cross(right, forward), fallback=(0.0, 1.0, 0.0))
    return _dot(delta, right), _dot(delta, corrected_up), -_dot(delta, forward)


def _normalized(
    value: tuple[float, float, float],
    *,
    fallback: tuple[float, float, float],
) -> tuple[float, float, float]:
    length = math.sqrt(_dot(value, value))
    if length <= 1e-9:
        return fallback
    return value[0] / length, value[1] / length, value[2] / length


def _dot(left: tuple[float, float, float], right: tuple[float, float, float]) -> float:
    return sum(left[index] * right[index] for index in range(3))


def _cross(
    left: tuple[float, float, float], right: tuple[float, float, float]
) -> tuple[float, float, float]:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )
