from __future__ import annotations

from collections import deque

import numpy as np
from numpy.typing import NDArray

from voxel_sandbox.domain.blocks import BlockRegistry
from voxel_sandbox.engine.chunks import CHUNK_HEIGHT, SECTION_SIZE, Chunk, DirtyFlag


def relight_chunk(chunk: Chunk, registry: BlockRegistry) -> None:
    blocks = _combine_blocks(chunk)
    opaque_lookup, emission_lookup = _block_lookups(registry)
    opaque = opaque_lookup[blocks]
    sky_light = _direct_skylight(opaque)
    block_light = _propagate_block_light(blocks, opaque, emission_lookup)

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


def _propagate_block_light(
    blocks: NDArray[np.uint16],
    opaque: NDArray[np.bool_],
    emission_lookup: NDArray[np.uint8],
) -> NDArray[np.uint8]:
    light = emission_lookup[blocks].copy()
    queue: deque[tuple[int, int, int]] = deque(
        (int(x), int(y), int(z)) for x, y, z in np.argwhere(light > 0)
    )
    while queue:
        x, y, z = queue.popleft()
        next_light = int(light[x, y, z]) - 1
        if next_light <= 0:
            continue
        for nx, ny, nz in (
            (x + 1, y, z),
            (x - 1, y, z),
            (x, y + 1, z),
            (x, y - 1, z),
            (x, y, z + 1),
            (x, y, z - 1),
        ):
            if not (0 <= nx < SECTION_SIZE and 0 <= ny < CHUNK_HEIGHT and 0 <= nz < SECTION_SIZE):
                continue
            if opaque[nx, ny, nz] or int(light[nx, ny, nz]) >= next_light:
                continue
            light[nx, ny, nz] = next_light
            queue.append((nx, ny, nz))
    return light
