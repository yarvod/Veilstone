from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass

from voxel_sandbox.engine.chunks import Chunk, ChunkCoord
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
            self._loaded[coord] = chunk
        return chunk

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
                self._loaded[coord] = chunk
                completed.append(chunk)
        return StreamBatch(tuple(completed), unloaded)

    def close(self) -> None:
        for future in self._pending.values():
            future.cancel()
        self._executor.shutdown(wait=True, cancel_futures=True)
        self._pending.clear()
        self._loaded.clear()

    def _desired_coords(self, center: ChunkCoord) -> set[ChunkCoord]:
        radius = self.render_distance
        return {
            ChunkCoord(center.x + dx, center.z + dz)
            for dx in range(-radius, radius + 1)
            for dz in range(-radius, radius + 1)
        }


def _distance_squared(first: ChunkCoord, second: ChunkCoord) -> int:
    return (first.x - second.x) ** 2 + (first.z - second.z) ** 2
