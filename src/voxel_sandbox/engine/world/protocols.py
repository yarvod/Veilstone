from __future__ import annotations

from typing import Protocol

from voxel_sandbox.engine.chunks import Chunk


class World(Protocol):
    def get_block(self, x: int, y: int, z: int) -> int: ...

    def set_block(self, x: int, y: int, z: int, block_id: int) -> None: ...

    def get_chunk(self, cx: int, cz: int) -> Chunk | None: ...
