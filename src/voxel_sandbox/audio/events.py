from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class VolumeGroup(Enum):
    MASTER = "master"
    EFFECTS = "effects"
    MUSIC = "music"
    AMBIENCE = "ambience"


class AudioEventKind(Enum):
    SOUND = auto()
    MUSIC = auto()
    AMBIENCE = auto()
    STOP_MUSIC = auto()
    STOP_AMBIENCE = auto()


@dataclass(frozen=True, slots=True)
class AudioEvent:
    kind: AudioEventKind
    key: str = ""
    position: tuple[float, float, float] | None = None
