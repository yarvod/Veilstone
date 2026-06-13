from __future__ import annotations

from enum import IntFlag, auto

import numpy as np
from numpy.typing import NDArray

from voxel_sandbox.engine.chunks.coordinates import SECTION_SIZE


class DirtyFlag(IntFlag):
    NONE = 0
    MESH = auto()
    LIGHTING = auto()
    SAVE = auto()


class ChunkSection:
    __slots__ = ("block_light", "blocks", "dirty", "metadata", "revision", "sky_light")

    def __init__(self) -> None:
        shape = (SECTION_SIZE, SECTION_SIZE, SECTION_SIZE)
        self.blocks: NDArray[np.uint16] = np.zeros(shape, dtype=np.uint16)
        self.block_light: NDArray[np.uint8] = np.zeros(shape, dtype=np.uint8)
        self.sky_light: NDArray[np.uint8] = np.zeros(shape, dtype=np.uint8)
        self.metadata: NDArray[np.uint8] = np.zeros(shape, dtype=np.uint8)
        self.dirty = DirtyFlag.NONE
        self.revision = 0

    def get_block(self, x: int, y: int, z: int) -> int:
        self._validate_local(x, y, z)
        return int(self.blocks[x, y, z])

    def set_block(self, x: int, y: int, z: int, block_id: int) -> bool:
        self._validate_local(x, y, z)
        if not 0 <= block_id <= 65535:
            raise ValueError("Block ID must fit into uint16")
        if int(self.blocks[x, y, z]) == block_id:
            return False
        self.blocks[x, y, z] = block_id
        self.dirty |= DirtyFlag.MESH | DirtyFlag.LIGHTING | DirtyFlag.SAVE
        self.revision += 1
        return True

    def clear_dirty(self, flags: DirtyFlag | None = None) -> None:
        if flags is None:
            self.dirty = DirtyFlag.NONE
        else:
            self.dirty &= ~flags

    @staticmethod
    def _validate_local(x: int, y: int, z: int) -> None:
        if not (0 <= x < SECTION_SIZE and 0 <= y < SECTION_SIZE and 0 <= z < SECTION_SIZE):
            raise IndexError(f"Local block coordinate out of range: {(x, y, z)}")
