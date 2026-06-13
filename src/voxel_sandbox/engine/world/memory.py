from __future__ import annotations

from voxel_sandbox.engine.chunks import CHUNK_HEIGHT, Chunk, ChunkCoord, split_world_axis


class InMemoryWorld:
    def __init__(self) -> None:
        self._chunks: dict[ChunkCoord, Chunk] = {}

    def get_chunk(self, cx: int, cz: int) -> Chunk | None:
        return self._chunks.get(ChunkCoord(cx, cz))

    def ensure_chunk(self, cx: int, cz: int) -> Chunk:
        coord = ChunkCoord(cx, cz)
        chunk = self._chunks.get(coord)
        if chunk is None:
            chunk = Chunk(coord)
            self._chunks[coord] = chunk
        return chunk

    def get_block(self, x: int, y: int, z: int) -> int:
        if not 0 <= y < CHUNK_HEIGHT:
            return 0
        chunk_x, local_x = split_world_axis(x)
        chunk_z, local_z = split_world_axis(z)
        chunk = self.get_chunk(chunk_x, chunk_z)
        if chunk is None:
            return 0
        return chunk.get_block(local_x, y, local_z)

    def set_block(self, x: int, y: int, z: int, block_id: int) -> None:
        if not 0 <= y < CHUNK_HEIGHT:
            raise IndexError(f"World Y coordinate out of range: {y}")
        chunk_x, local_x = split_world_axis(x)
        chunk_z, local_z = split_world_axis(z)
        self.ensure_chunk(chunk_x, chunk_z).set_block(local_x, y, local_z, block_id)
