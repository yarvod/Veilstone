from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass

from voxel_sandbox.engine.chunks import (
    CHUNK_HEIGHT,
    SECTION_SIZE,
    Chunk,
    ChunkCoord,
    split_world_axis,
)
from voxel_sandbox.engine.generation.terrain import TerrainGenerator


@dataclass(frozen=True, slots=True)
class StreamBatch:
    loaded: tuple[Chunk, ...]
    unloaded: tuple[ChunkCoord, ...]


class ChunkStreamer:
    def __init__(
        self,
        generator: TerrainGenerator,
        *,
        render_distance: int,
        workers: int,
    ) -> None:
        if render_distance < 0:
            raise ValueError("Render distance cannot be negative")
        if workers < 1:
            raise ValueError("At least one generation worker is required")
        self.generator = generator
        self.render_distance = render_distance
        self._executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="worldgen")
        self._loaded: dict[ChunkCoord, Chunk] = {}
        self._pending: dict[ChunkCoord, Future[Chunk]] = {}
        self._desired: set[ChunkCoord] = set()
        self._overrides: dict[tuple[int, int, int], int] = {}

    @property
    def loaded_count(self) -> int:
        return len(self._loaded)

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    def prime(self, coord: ChunkCoord) -> Chunk:
        chunk = self._loaded.get(coord)
        if chunk is None:
            chunk = self.generator.generate_chunk(coord)
            self._apply_overrides(chunk)
            self._loaded[coord] = chunk
        return chunk

    def get_chunk(self, coord: ChunkCoord) -> Chunk | None:
        return self._loaded.get(coord)

    def loaded_chunks(self) -> tuple[Chunk, ...]:
        return tuple(self._loaded.values())

    def get_block(self, x: int, y: int, z: int) -> int:
        if not 0 <= y < CHUNK_HEIGHT:
            return 0
        chunk_x, local_x = split_world_axis(x)
        chunk_z, local_z = split_world_axis(z)
        chunk = self.get_chunk(ChunkCoord(chunk_x, chunk_z))
        if chunk is None:
            return 0
        return chunk.get_block(local_x, y, local_z)

    def set_block(self, x: int, y: int, z: int, block_id: int) -> bool:
        if not 0 <= y < CHUNK_HEIGHT:
            return False
        chunk_x, local_x = split_world_axis(x)
        chunk_z, local_z = split_world_axis(z)
        chunk = self.get_chunk(ChunkCoord(chunk_x, chunk_z))
        if chunk is None:
            return False
        changed = chunk.set_block(local_x, y, local_z, block_id)
        if changed:
            self._overrides[(x, y, z)] = block_id
        return changed

    def update(self, center: ChunkCoord, *, max_completed: int) -> StreamBatch:
        self._desired = self._desired_coords(center)
        unloaded = tuple(coord for coord in self._loaded if coord not in self._desired)
        for coord in unloaded:
            del self._loaded[coord]

        for coord, future in tuple(self._pending.items()):
            if coord not in self._desired and future.cancel():
                del self._pending[coord]

        missing = self._desired - self._loaded.keys() - self._pending.keys()
        for coord in sorted(missing, key=lambda item: _distance_squared(item, center)):
            self._pending[coord] = self._executor.submit(self.generator.generate_chunk, coord)

        completed: list[Chunk] = []
        for coord, future in tuple(self._pending.items()):
            if len(completed) >= max_completed or not future.done():
                continue
            del self._pending[coord]
            chunk = future.result()
            if coord in self._desired:
                self._apply_overrides(chunk)
                self._loaded[coord] = chunk
                completed.append(chunk)
        return StreamBatch(tuple(completed), unloaded)

    def close(self) -> None:
        for future in self._pending.values():
            future.cancel()
        self._executor.shutdown(wait=True, cancel_futures=True)
        self._pending.clear()
        self._loaded.clear()
        self._overrides.clear()

    def _desired_coords(self, center: ChunkCoord) -> set[ChunkCoord]:
        radius = self.render_distance
        return {
            ChunkCoord(center.x + dx, center.z + dz)
            for dx in range(-radius, radius + 1)
            for dz in range(-radius, radius + 1)
        }

    def _apply_overrides(self, chunk: Chunk) -> None:
        min_x = chunk.coord.x * SECTION_SIZE
        min_z = chunk.coord.z * SECTION_SIZE
        for (x, y, z), block_id in self._overrides.items():
            if min_x <= x < min_x + SECTION_SIZE and min_z <= z < min_z + SECTION_SIZE:
                chunk.set_block(x - min_x, y, z - min_z, block_id)


def _distance_squared(first: ChunkCoord, second: ChunkCoord) -> int:
    return (first.x - second.x) ** 2 + (first.z - second.z) ** 2
