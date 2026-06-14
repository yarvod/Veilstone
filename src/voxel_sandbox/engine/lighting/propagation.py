from __future__ import annotations

from collections.abc import Iterable

import numpy as np
from numpy.typing import NDArray

from voxel_sandbox.domain.blocks import BlockRegistry
from voxel_sandbox.engine.chunks import CHUNK_HEIGHT, SECTION_SIZE, Chunk, DirtyFlag


def relight_chunk(chunk: Chunk, registry: BlockRegistry) -> None:
    relight_chunks((chunk,), registry)


def relight_chunks(chunks: Iterable[Chunk], registry: BlockRegistry) -> tuple[Chunk, ...]:
    chunk_list = tuple(chunks)
    if not chunk_list:
        return ()
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
    sky_light = _propagate_light(_direct_skylight(opaque), opaque)
    block_light = _propagate_light(emission_lookup[blocks], opaque)

    changed_chunks: list[Chunk] = []
    for coord, chunk in by_coord.items():
        start_x = (coord.x - min_chunk_x) * SECTION_SIZE
        start_z = (coord.z - min_chunk_z) * SECTION_SIZE
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
    light = sources.copy()
    blocked = opaque & (sources == 0)
    for _ in range(15):
        attenuated = np.where(light > 0, light - 1, 0).astype(np.uint8)
        neighbors = np.zeros_like(light)
        neighbors[1:, :, :] = np.maximum(neighbors[1:, :, :], attenuated[:-1, :, :])
        neighbors[:-1, :, :] = np.maximum(neighbors[:-1, :, :], attenuated[1:, :, :])
        neighbors[:, 1:, :] = np.maximum(neighbors[:, 1:, :], attenuated[:, :-1, :])
        neighbors[:, :-1, :] = np.maximum(neighbors[:, :-1, :], attenuated[:, 1:, :])
        neighbors[:, :, 1:] = np.maximum(neighbors[:, :, 1:], attenuated[:, :, :-1])
        neighbors[:, :, :-1] = np.maximum(neighbors[:, :, :-1], attenuated[:, :, 1:])
        updated = np.maximum(sources, neighbors)
        updated[blocked] = 0
        if np.array_equal(updated, light):
            break
        light = updated
    return light
