from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from voxel_sandbox.domain.blocks import BlockRegistry
from voxel_sandbox.engine.chunks import CHUNK_HEIGHT, SECTION_SIZE, Chunk, DirtyFlag


def relight_chunk(chunk: Chunk, registry: BlockRegistry) -> None:
    blocks = _combine_blocks(chunk)
    opaque_lookup, emission_lookup = _block_lookups(registry)
    opaque = opaque_lookup[blocks]
    sky_light = _propagate_light(_direct_skylight(opaque), opaque)
    block_light = _propagate_light(emission_lookup[blocks], opaque)

    for section_y, section in enumerate(chunk.sections):
        start = section_y * SECTION_SIZE
        end = start + SECTION_SIZE
        section.sky_light[:] = sky_light[:, start:end, :]
        section.block_light[:] = block_light[:, start:end, :]
        section.dirty |= DirtyFlag.MESH | DirtyFlag.LIGHTING


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
    open_columns = np.ones((SECTION_SIZE, SECTION_SIZE), dtype=np.bool_)
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
