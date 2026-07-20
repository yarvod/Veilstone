from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Executor, Future, ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import NDArray

from voxel_sandbox.engine.chunks import (
    CHUNK_HEIGHT,
    SECTION_SIZE,
    Chunk,
    ChunkCoord,
    DirtyFlag,
    split_world_axis,
)
from voxel_sandbox.engine.generation.terrain import TerrainGenerator
from voxel_sandbox.engine.perf.process_priority import lower_background_process_priority
from voxel_sandbox.infrastructure.storage import WorldStorage


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
        postprocess: Callable[[Chunk], None] | None = None,
        backend: Literal["thread", "process"] = "thread",
        prepare_lighting: bool = False,
        storage: WorldStorage | None = None,
    ) -> None:
        if render_distance < 0:
            raise ValueError("Render distance cannot be negative")
        if workers < 1:
            raise ValueError("At least one generation worker is required")
        if backend not in {"thread", "process"}:
            raise ValueError(f"Unsupported generation backend: {backend}")
        self.generator = generator
        self.render_distance = render_distance
        self._postprocess = postprocess
        self._prepare_lighting = prepare_lighting
        self._backend = backend
        self._storage = storage
        self._executor: Executor
        if backend == "process":
            if postprocess is not None:
                raise ValueError("Process worldgen uses prepare_lighting instead of postprocess")
            self._executor = ProcessPoolExecutor(
                max_workers=workers,
                initializer=lower_background_process_priority,
            )
            _warm_process_pool(self._executor, workers)
        else:
            self._executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="worldgen")
        self._loaded: dict[ChunkCoord, Chunk] = {}
        self._pending: dict[ChunkCoord, Future[Chunk]] = {}
        self._deferred_saves: dict[ChunkCoord, Chunk] = {}
        self._desired: set[ChunkCoord] = set()
        self._overrides: dict[tuple[int, int, int], int] = {}
        self._metadata_overrides: dict[tuple[int, int, int], int] = {}

    @property
    def loaded_count(self) -> int:
        return len(self._loaded)

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    @property
    def pending_save_count(self) -> int:
        return len(self._deferred_saves)

    def prime(self, coord: ChunkCoord) -> Chunk:
        chunk = self._loaded.get(coord)
        if chunk is None:
            chunk = self._deferred_saves.pop(coord, None)
        if chunk is None:
            chunk = self._generate_chunk(coord)
            self._apply_overrides(chunk)
            self._loaded[coord] = chunk
        else:
            self._loaded[coord] = chunk
        return chunk

    def get_chunk(self, coord: ChunkCoord) -> Chunk | None:
        return self._loaded.get(coord)

    def loaded_chunks(self) -> tuple[Chunk, ...]:
        return tuple(self._loaded.values())

    def set_render_distance(self, render_distance: int) -> bool:
        if render_distance < 0:
            raise ValueError("Render distance cannot be negative")
        if render_distance == self.render_distance:
            return False
        self.render_distance = render_distance
        return True

    def install_chunk(self, chunk: Chunk) -> None:
        pending = self._pending.pop(chunk.coord, None)
        if pending is not None:
            pending.cancel()
        self._deferred_saves.pop(chunk.coord, None)
        self._apply_overrides(chunk)
        self._loaded[chunk.coord] = chunk

    def get_block(self, x: int, y: int, z: int) -> int:
        if not 0 <= y < CHUNK_HEIGHT:
            return 0
        chunk_x, local_x = split_world_axis(x)
        chunk_z, local_z = split_world_axis(z)
        chunk = self.get_chunk(ChunkCoord(chunk_x, chunk_z))
        if chunk is None:
            return 0
        return chunk.get_block(local_x, y, local_z)

    def get_light(self, x: int, y: int, z: int) -> tuple[int, int]:
        if not 0 <= y < CHUNK_HEIGHT:
            return 0, 0
        chunk_x, local_x = split_world_axis(x)
        chunk_z, local_z = split_world_axis(z)
        chunk = self.get_chunk(ChunkCoord(chunk_x, chunk_z))
        if chunk is None:
            return 0, 0
        section_y, local_y = divmod(y, SECTION_SIZE)
        section = chunk.sections[section_y]
        return (
            int(section.sky_light[local_x, local_y, local_z]),
            int(section.block_light[local_x, local_y, local_z]),
        )

    def get_metadata(self, x: int, y: int, z: int) -> int:
        if not 0 <= y < CHUNK_HEIGHT:
            return 0
        chunk_x, local_x = split_world_axis(x)
        chunk_z, local_z = split_world_axis(z)
        chunk = self.get_chunk(ChunkCoord(chunk_x, chunk_z))
        if chunk is None:
            return 0
        section_y, local_y = divmod(y, SECTION_SIZE)
        return int(chunk.sections[section_y].metadata[local_x, local_y, local_z])

    def snapshot_region(
        self,
        origin: tuple[int, int, int],
        shape: tuple[int, int, int],
    ) -> tuple[
        NDArray[np.uint16],
        NDArray[np.uint8],
        NDArray[np.uint8],
        NDArray[np.uint8],
    ]:
        blocks = np.zeros(shape, dtype=np.uint16)
        sky_light = np.zeros(shape, dtype=np.uint8)
        block_light = np.zeros(shape, dtype=np.uint8)
        metadata = np.zeros(shape, dtype=np.uint8)
        end_x = origin[0] + shape[0]
        end_y = origin[1] + shape[1]
        end_z = origin[2] + shape[2]
        for chunk_x in range(origin[0] // SECTION_SIZE, (end_x - 1) // SECTION_SIZE + 1):
            for chunk_z in range(origin[2] // SECTION_SIZE, (end_z - 1) // SECTION_SIZE + 1):
                chunk = self.get_chunk(ChunkCoord(chunk_x, chunk_z))
                if chunk is None:
                    continue
                source_x_start = max(origin[0], chunk_x * SECTION_SIZE)
                source_x_end = min(end_x, (chunk_x + 1) * SECTION_SIZE)
                source_z_start = max(origin[2], chunk_z * SECTION_SIZE)
                source_z_end = min(end_z, (chunk_z + 1) * SECTION_SIZE)
                for section_y, section in enumerate(chunk.sections):
                    section_start_y = section_y * SECTION_SIZE
                    source_y_start = max(origin[1], section_start_y, 0)
                    source_y_end = min(end_y, section_start_y + SECTION_SIZE, CHUNK_HEIGHT)
                    if source_y_start >= source_y_end:
                        continue
                    source = (
                        slice(
                            source_x_start - chunk_x * SECTION_SIZE,
                            source_x_end - chunk_x * SECTION_SIZE,
                        ),
                        slice(source_y_start - section_start_y, source_y_end - section_start_y),
                        slice(
                            source_z_start - chunk_z * SECTION_SIZE,
                            source_z_end - chunk_z * SECTION_SIZE,
                        ),
                    )
                    target = (
                        slice(source_x_start - origin[0], source_x_end - origin[0]),
                        slice(source_y_start - origin[1], source_y_end - origin[1]),
                        slice(source_z_start - origin[2], source_z_end - origin[2]),
                    )
                    blocks[target] = section.blocks[source]
                    sky_light[target] = section.sky_light[source]
                    block_light[target] = section.block_light[source]
                    metadata[target] = section.metadata[source]
        return blocks, sky_light, block_light, metadata

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
            self._metadata_overrides.pop((x, y, z), None)
        return changed

    def set_fluid(self, x: int, y: int, z: int, block_id: int, level: int) -> bool:
        if not 1 <= level <= 8 or not 0 <= y < CHUNK_HEIGHT:
            return False
        chunk_x, local_x = split_world_axis(x)
        chunk_z, local_z = split_world_axis(z)
        chunk = self.get_chunk(ChunkCoord(chunk_x, chunk_z))
        if chunk is None:
            return False
        changed = chunk.set_block(local_x, y, local_z, block_id)
        changed = chunk.set_metadata(local_x, y, local_z, level) or changed
        if changed:
            self._overrides[(x, y, z)] = block_id
            self._metadata_overrides[(x, y, z)] = level
        return changed

    def update(
        self,
        center: ChunkCoord,
        *,
        max_completed: int,
        max_submitted: int | None = None,
    ) -> StreamBatch:
        self._desired = self._desired_coords(center)
        restored: list[Chunk] = []
        restore_coords = tuple(self._desired & self._deferred_saves.keys())[:max_completed]
        for coord in restore_coords:
            self._loaded[coord] = self._deferred_saves.pop(coord)
            restored.append(self._loaded[coord])
        unloaded = tuple(coord for coord in self._loaded if coord not in self._desired)
        for coord in unloaded:
            chunk = self._loaded.pop(coord)
            if self._storage is not None and self._needs_save(chunk):
                self._deferred_saves[coord] = chunk

        self._drain_deferred_saves(1)

        for coord, future in tuple(self._pending.items()):
            if coord not in self._desired and future.cancel():
                del self._pending[coord]

        missing = (
            self._desired - self._loaded.keys() - self._pending.keys() - self._deferred_saves.keys()
        )
        missing_coords = sorted(missing, key=lambda item: _distance_squared(item, center))
        if max_submitted is not None:
            if max_submitted < 0:
                raise ValueError("max_submitted cannot be negative")
            missing_coords = missing_coords[:max_submitted]
        for coord in missing_coords:
            if self._backend == "process":
                self._pending[coord] = self._executor.submit(
                    _generate_chunk_task,
                    self.generator,
                    coord,
                    self._prepare_lighting,
                    self._storage,
                )
            else:
                self._pending[coord] = self._executor.submit(self._generate_chunk, coord)

        completed = restored
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
        self.save_dirty()
        for future in self._pending.values():
            future.cancel()
        self._executor.shutdown(wait=True, cancel_futures=True)
        self._pending.clear()
        self._loaded.clear()
        self._deferred_saves.clear()
        self._overrides.clear()
        self._metadata_overrides.clear()

    def save_dirty(self) -> int:
        if self._storage is None:
            return 0
        saved = 0
        chunks = {**self._deferred_saves, **self._loaded}
        for chunk in chunks.values():
            if self._save_chunk_if_dirty(chunk):
                saved += 1
        return saved

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
                metadata = self._metadata_overrides.get((x, y, z))
                if metadata is not None:
                    chunk.set_metadata(x - min_x, y, z - min_z, metadata)

    def _generate_chunk(self, coord: ChunkCoord) -> Chunk:
        if self._storage is not None:
            saved = self._storage.load_chunk(coord)
            if saved is not None:
                return saved
        chunk = self.generator.generate_chunk(coord)
        if self._prepare_lighting:
            from voxel_sandbox.domain.blocks import create_core_block_registry
            from voxel_sandbox.engine.lighting import relight_chunk

            relight_chunk(chunk, create_core_block_registry())
        if self._postprocess is not None:
            self._postprocess(chunk)
        return chunk

    def _save_chunk_if_dirty(self, chunk: Chunk) -> bool:
        if self._storage is None or not self._needs_save(chunk):
            return False
        self._storage.save_chunk(chunk)
        return True

    @staticmethod
    def _needs_save(chunk: Chunk) -> bool:
        return any(section.dirty & DirtyFlag.SAVE for section in chunk.sections)

    def _drain_deferred_saves(self, limit: int) -> None:
        saveable = (coord for coord in self._deferred_saves if coord not in self._desired)
        for coord in tuple(saveable)[:limit]:
            chunk = self._deferred_saves.pop(coord)
            self._save_chunk_if_dirty(chunk)


def _generate_chunk_task(
    generator: TerrainGenerator,
    coord: ChunkCoord,
    prepare_lighting: bool,
    storage: WorldStorage | None,
) -> Chunk:
    if storage is not None:
        saved = storage.load_chunk(coord)
        if saved is not None:
            return saved
    chunk = generator.generate_chunk(coord)
    if prepare_lighting:
        from voxel_sandbox.domain.blocks import create_core_block_registry
        from voxel_sandbox.engine.lighting import relight_chunk

        relight_chunk(chunk, create_core_block_registry())
    return chunk


def _distance_squared(first: ChunkCoord, second: ChunkCoord) -> int:
    return (first.x - second.x) ** 2 + (first.z - second.z) ** 2


def _warm_process_pool(executor: Executor, workers: int) -> None:
    futures = [executor.submit(_process_ready) for _ in range(workers)]
    for future in futures:
        future.result()


def _process_ready() -> bool:
    return True
