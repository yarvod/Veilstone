from __future__ import annotations

from typing import Final

from voxel_sandbox.engine.chunks.coordinates import SECTION_SIZE, ChunkCoord
from voxel_sandbox.engine.chunks.section import ChunkSection

CHUNK_HEIGHT: Final = 128
SECTION_COUNT: Final = CHUNK_HEIGHT // SECTION_SIZE


class Chunk:
    __slots__ = ("coord", "sections")

    def __init__(self, coord: ChunkCoord) -> None:
        self.coord = coord
        self.sections = tuple(ChunkSection() for _ in range(SECTION_COUNT))

    def get_block(self, x: int, y: int, z: int) -> int:
        section, local_y = self._split_y(y)
        return self.sections[section].get_block(x, local_y, z)

    def set_block(self, x: int, y: int, z: int, block_id: int) -> bool:
        section, local_y = self._split_y(y)
        return self.sections[section].set_block(x, local_y, z, block_id)

    @staticmethod
    def _split_y(y: int) -> tuple[int, int]:
        if not 0 <= y < CHUNK_HEIGHT:
            raise IndexError(f"World Y coordinate out of range: {y}")
        return divmod(y, SECTION_SIZE)
