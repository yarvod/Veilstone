from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from voxel_sandbox.engine.chunks import SECTION_SIZE, Chunk

WATER_BLOCK_ID = 8
FLUID_MAX_LEVEL = 8


@dataclass(frozen=True, slots=True)
class FluidUpdate:
    changed_blocks: int

    @property
    def changed(self) -> bool:
        return self.changed_blocks > 0


def simulate_water_step(chunk: Chunk, *, water_id: int = WATER_BLOCK_ID) -> FluidUpdate:
    """Advance one deterministic, non-cascading water step inside a chunk."""
    blocks = np.concatenate([section.blocks for section in chunk.sections], axis=1)
    metadata = np.concatenate([section.metadata for section in chunk.sections], axis=1)
    proposals: dict[tuple[int, int, int], int] = {}

    for raw_x, raw_y, raw_z in np.argwhere(blocks == water_id):
        x, y, z = int(raw_x), int(raw_y), int(raw_z)
        level = int(metadata[x, y, z]) or FLUID_MAX_LEVEL
        if y > 0 and int(blocks[x, y - 1, z]) == 0:
            proposals[(x, y - 1, z)] = max(proposals.get((x, y - 1, z), 0), level)
            continue
        if level <= 1:
            continue
        spread_level = level - 1
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            neighbor_x, neighbor_z = x + dx, z + dz
            if not (0 <= neighbor_x < SECTION_SIZE and 0 <= neighbor_z < SECTION_SIZE):
                continue
            neighbor_id = int(blocks[neighbor_x, y, neighbor_z])
            neighbor_level = int(metadata[neighbor_x, y, neighbor_z])
            if neighbor_id == 0 or (neighbor_id == water_id and neighbor_level < spread_level):
                position = (neighbor_x, y, neighbor_z)
                proposals[position] = max(proposals.get(position, 0), spread_level)

    changed = 0
    for (x, y, z), level in proposals.items():
        if chunk.get_block(x, y, z) != water_id:
            chunk.set_block(x, y, z, water_id)
            changed += 1
        if chunk.set_metadata(x, y, z, level):
            changed += 1
    return FluidUpdate(changed)
