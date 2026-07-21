from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from voxel_sandbox.domain.blocks import BlockRegistry
from voxel_sandbox.engine.chunks import CHUNK_HEIGHT, SECTION_SIZE, Chunk, DirtyFlag
from voxel_sandbox.engine.perf.light_propagation import propagate_light


def relight_chunk(chunk: Chunk, registry: BlockRegistry) -> None:
    relight_chunks((chunk,), registry)


def relight_chunks(chunks: Iterable[Chunk], registry: BlockRegistry) -> tuple[Chunk, ...]:
    volume = _prepare_relight_volume(chunks, registry)
    if volume is None:
        return ()
    sky_light = _propagate_light(volume.sky_sources, volume.opaque)
    block_light = _propagate_light(volume.block_sources, volume.opaque)
    return _apply_relight_volume(volume, sky_light, block_light)


class RelightChunksJob:
    """Incrementally produce the same result as ``relight_chunks``."""

    def __init__(self, chunks: Iterable[Chunk], registry: BlockRegistry) -> None:
        self._volume = _prepare_relight_volume(chunks, registry)
        self._changed_chunks: tuple[Chunk, ...] | None = None
        if self._volume is None:
            self._sky_job = None
            self._block_job = None
            self._changed_chunks = ()
            return
        self._sky_job = _LightPropagationJob(
            self._volume.sky_sources,
            self._volume.opaque,
        )
        self._block_job = _LightPropagationJob(
            self._volume.block_sources,
            self._volume.opaque,
        )
        self._complete_if_ready()

    @property
    def done(self) -> bool:
        return self._changed_chunks is not None

    @property
    def changed_chunks(self) -> tuple[Chunk, ...]:
        if self._changed_chunks is None:
            raise RuntimeError("Relight job has not completed")
        return self._changed_chunks

    def step(self, iterations: int = 1) -> bool:
        if iterations < 1:
            raise ValueError("Relight iterations must be positive")
        if self.done:
            return True
        assert self._sky_job is not None
        assert self._block_job is not None
        for _ in range(iterations):
            if not self._sky_job.done:
                self._sky_job.step()
            elif not self._block_job.done:
                self._block_job.step()
            else:
                break
        self._complete_if_ready()
        return self.done

    def _complete_if_ready(self) -> None:
        if self._volume is None or self._changed_chunks is not None:
            return
        assert self._sky_job is not None
        assert self._block_job is not None
        if not self._sky_job.done or not self._block_job.done:
            return
        self._changed_chunks = _apply_relight_volume(
            self._volume,
            self._sky_job.result,
            self._block_job.result,
        )


@dataclass(slots=True)
class _RelightVolume:
    chunks: tuple[Chunk, ...]
    min_chunk_x: int
    min_chunk_z: int
    opaque: NDArray[np.bool_]
    sky_sources: NDArray[np.uint8]
    block_sources: NDArray[np.uint8]


class _LightPropagationJob:
    def __init__(
        self,
        sources: NDArray[np.uint8],
        opaque: NDArray[np.bool_],
    ) -> None:
        self._sources = sources
        self._light = sources.copy()
        self._blocked = opaque & (sources == 0)
        self._attenuated = np.empty_like(self._light)
        self._neighbors = np.empty_like(self._light)
        self._updated = np.empty_like(self._light)
        self._iterations = 0
        self.done = not np.any(self._light)

    @property
    def result(self) -> NDArray[np.uint8]:
        if not self.done:
            raise RuntimeError("Light propagation job has not completed")
        return self._light

    def step(self) -> None:
        if self.done:
            return
        np.maximum(self._light, 1, out=self._attenuated)
        np.subtract(self._attenuated, 1, out=self._attenuated)
        self._neighbors.fill(0)
        np.maximum(
            self._neighbors[1:, :, :],
            self._attenuated[:-1, :, :],
            out=self._neighbors[1:, :, :],
        )
        np.maximum(
            self._neighbors[:-1, :, :],
            self._attenuated[1:, :, :],
            out=self._neighbors[:-1, :, :],
        )
        np.maximum(
            self._neighbors[:, 1:, :],
            self._attenuated[:, :-1, :],
            out=self._neighbors[:, 1:, :],
        )
        np.maximum(
            self._neighbors[:, :-1, :],
            self._attenuated[:, 1:, :],
            out=self._neighbors[:, :-1, :],
        )
        np.maximum(
            self._neighbors[:, :, 1:],
            self._attenuated[:, :, :-1],
            out=self._neighbors[:, :, 1:],
        )
        np.maximum(
            self._neighbors[:, :, :-1],
            self._attenuated[:, :, 1:],
            out=self._neighbors[:, :, :-1],
        )
        np.maximum(self._sources, self._neighbors, out=self._updated)
        self._updated[self._blocked] = 0
        self._iterations += 1
        if np.array_equal(self._updated, self._light):
            self.done = True
            return
        self._light, self._updated = self._updated, self._light
        self.done = self._iterations >= 15


def _prepare_relight_volume(
    chunks: Iterable[Chunk],
    registry: BlockRegistry,
) -> _RelightVolume | None:
    chunk_list = tuple(chunks)
    if not chunk_list:
        return None
    by_coord = {chunk.coord: chunk for chunk in chunk_list}
    if len(by_coord) != len(chunk_list):
        raise ValueError("Chunk coordinates must be unique during relighting")
    min_chunk_x = min(coord.x for coord in by_coord)
    max_chunk_x = max(coord.x for coord in by_coord)
    min_chunk_z = min(coord.z for coord in by_coord)
    max_chunk_z = max(coord.z for coord in by_coord)
    width = (max_chunk_x - min_chunk_x + 1) * SECTION_SIZE
    depth = (max_chunk_z - min_chunk_z + 1) * SECTION_SIZE
    blocks = np.zeros((width, CHUNK_HEIGHT, depth), dtype=np.uint16)
    loaded = np.zeros((width, CHUNK_HEIGHT, depth), dtype=np.bool_)
    for coord, chunk in by_coord.items():
        start_x = (coord.x - min_chunk_x) * SECTION_SIZE
        start_z = (coord.z - min_chunk_z) * SECTION_SIZE
        target = (
            slice(start_x, start_x + SECTION_SIZE),
            slice(None),
            slice(start_z, start_z + SECTION_SIZE),
        )
        blocks[target] = _combine_blocks(chunk)
        loaded[target] = True

    opaque_lookup, emission_lookup = _block_lookups(registry)
    opaque = opaque_lookup[blocks] | ~loaded
    return _RelightVolume(
        chunks=chunk_list,
        min_chunk_x=min_chunk_x,
        min_chunk_z=min_chunk_z,
        opaque=opaque,
        sky_sources=_direct_skylight(opaque),
        block_sources=emission_lookup[blocks],
    )


def _apply_relight_volume(
    volume: _RelightVolume,
    sky_light: NDArray[np.uint8],
    block_light: NDArray[np.uint8],
) -> tuple[Chunk, ...]:
    changed_chunks: list[Chunk] = []
    for chunk in volume.chunks:
        start_x = (chunk.coord.x - volume.min_chunk_x) * SECTION_SIZE
        start_z = (chunk.coord.z - volume.min_chunk_z) * SECTION_SIZE
        chunk_changed = False
        for section_y, section in enumerate(chunk.sections):
            start_y = section_y * SECTION_SIZE
            next_sky_light = sky_light[
                start_x : start_x + SECTION_SIZE,
                start_y : start_y + SECTION_SIZE,
                start_z : start_z + SECTION_SIZE,
            ]
            next_block_light = block_light[
                start_x : start_x + SECTION_SIZE,
                start_y : start_y + SECTION_SIZE,
                start_z : start_z + SECTION_SIZE,
            ]
            if np.array_equal(section.sky_light, next_sky_light) and np.array_equal(
                section.block_light, next_block_light
            ):
                continue
            section.sky_light[:] = next_sky_light
            section.block_light[:] = next_block_light
            section.dirty |= DirtyFlag.MESH | DirtyFlag.LIGHTING
            chunk_changed = True
        if chunk_changed:
            changed_chunks.append(chunk)
    return tuple(changed_chunks)


def _combine_blocks(chunk: Chunk) -> NDArray[np.uint16]:
    return np.concatenate([section.blocks for section in chunk.sections], axis=1)


def _block_lookups(registry: BlockRegistry) -> tuple[NDArray[np.bool_], NDArray[np.uint8]]:
    max_block_id = max((definition.id for definition in registry), default=0)
    opaque = np.zeros(max_block_id + 1, dtype=np.bool_)
    emission = np.zeros(max_block_id + 1, dtype=np.uint8)
    for definition in registry:
        opaque[definition.id] = definition.is_opaque
        emission[definition.id] = definition.emits_light
    return opaque, emission


def _direct_skylight(opaque: NDArray[np.bool_]) -> NDArray[np.uint8]:
    sky = np.zeros(opaque.shape, dtype=np.uint8)
    open_columns = np.ones((opaque.shape[0], opaque.shape[2]), dtype=np.bool_)
    for y in range(CHUNK_HEIGHT - 1, -1, -1):
        open_columns &= ~opaque[:, y, :]
        sky[:, y, :] = np.where(open_columns, 15, 0)
    return sky


def _propagate_light(sources: NDArray[np.uint8], opaque: NDArray[np.bool_]) -> NDArray[np.uint8]:
    return propagate_light(sources, opaque)
