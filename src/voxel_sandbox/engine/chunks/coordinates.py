from __future__ import annotations

from dataclasses import dataclass
from typing import Final

SECTION_SIZE: Final = 16


@dataclass(frozen=True, slots=True)
class ChunkCoord:
    x: int
    z: int


@dataclass(frozen=True, slots=True)
class SectionCoord:
    x: int
    y: int
    z: int

    @property
    def chunk(self) -> ChunkCoord:
        return ChunkCoord(self.x, self.z)


def split_world_axis(value: int) -> tuple[int, int]:
    """Return section coordinate and local coordinate, including for negatives."""
    return divmod(value, SECTION_SIZE)
