from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from voxel_sandbox.engine.chunks import CHUNK_HEIGHT, SECTION_SIZE, Chunk

WATER_BLOCK_ID = 8
FLUID_MAX_LEVEL = 8


@dataclass(frozen=True, slots=True)
class FluidUpdate:
    changed_blocks: int
    neighbor_keys: frozenset[tuple[int, int]] = frozenset()

    @property
    def changed(self) -> bool:
        return self.changed_blocks > 0

    @property
    def any_changed(self) -> bool:
        return self.changed_blocks > 0 or bool(self.neighbor_keys)


def _is_source(level: int) -> bool:
    return level == 0 or level >= FLUID_MAX_LEVEL


def _chunk_get_metadata(chunk: Chunk, x: int, y: int, z: int) -> int:
    section_idx, local_y = divmod(y, 16)
    if section_idx >= len(chunk.sections):
        return 0
    return int(chunk.sections[section_idx].metadata[x, local_y, z])


def _neighbor_key(nx: int, nz: int) -> tuple[int, int]:
    dx = 0 if 0 <= nx < SECTION_SIZE else (-1 if nx < 0 else 1)
    dz = 0 if 0 <= nz < SECTION_SIZE else (-1 if nz < 0 else 1)
    return dx, dz


def _local_coords(nx: int, nz: int) -> tuple[int, int]:
    lx = nx if 0 <= nx < SECTION_SIZE else (15 if nx < 0 else 0)
    lz = nz if 0 <= nz < SECTION_SIZE else (15 if nz < 0 else 0)
    return lx, lz


def simulate_water_step(
    chunk: Chunk,
    neighbors: dict[tuple[int, int], Chunk] | None = None,
    *,
    water_id: int = WATER_BLOCK_ID,
) -> FluidUpdate:
    """Advance one deterministic water step within a chunk and optionally into neighbors."""
    blocks = np.concatenate([section.blocks for section in chunk.sections], axis=1)
    metadata = np.concatenate([section.metadata for section in chunk.sections], axis=1)

    def get_block_nb(nx: int, y: int, nz: int) -> int:
        if 0 <= nx < SECTION_SIZE and 0 <= nz < SECTION_SIZE:
            return int(blocks[nx, y, nz])
        if neighbors is None:
            return -1
        nb = neighbors.get(_neighbor_key(nx, nz))
        if nb is None:
            return -1
        lx, lz = _local_coords(nx, nz)
        return nb.get_block(lx, y, lz)

    def get_meta_nb(nx: int, y: int, nz: int) -> int:
        if 0 <= nx < SECTION_SIZE and 0 <= nz < SECTION_SIZE:
            return int(metadata[nx, y, nz])
        if neighbors is None:
            return 0
        nb = neighbors.get(_neighbor_key(nx, nz))
        if nb is None:
            return 0
        lx, lz = _local_coords(nx, nz)
        return _chunk_get_metadata(nb, lx, y, lz)

    proposals: dict[tuple[int, int, int], int] = {}
    # neighbor_proposals[(dx, dz)][(lx, y, lz)] = level
    neighbor_proposals: dict[tuple[int, int], dict[tuple[int, int, int], int]] = {}
    drain: list[tuple[int, int, int]] = []

    for raw_x, raw_y, raw_z in np.argwhere(blocks == water_id):
        x, y, z = int(raw_x), int(raw_y), int(raw_z)
        level = int(metadata[x, y, z]) or FLUID_MAX_LEVEL

        if not _is_source(level):
            has_support = False
            if y + 1 < CHUNK_HEIGHT and int(blocks[x, y + 1, z]) == water_id:
                has_support = True
            if not has_support:
                for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nb_id = get_block_nb(x + dx, y, z + dz)
                    if nb_id == water_id:
                        nb_level = get_meta_nb(x + dx, y, z + dz) or FLUID_MAX_LEVEL
                        if nb_level > level:
                            has_support = True
                            break
            if not has_support:
                drain.append((x, y, z))
                continue

        # Fall down first
        if y > 0 and int(blocks[x, y - 1, z]) == 0:
            proposals[(x, y - 1, z)] = max(proposals.get((x, y - 1, z), 0), FLUID_MAX_LEVEL)
            continue
        if level <= 1:
            continue
        spread_level = level - 1
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, nz = x + dx, z + dz
            if 0 <= nx < SECTION_SIZE and 0 <= nz < SECTION_SIZE:
                neighbor_id = int(blocks[nx, y, nz])
                neighbor_level = int(metadata[nx, y, nz])
                if neighbor_id == 0 or (neighbor_id == water_id and neighbor_level < spread_level):
                    pos = (nx, y, nz)
                    proposals[pos] = max(proposals.get(pos, 0), spread_level)
            elif neighbors is not None:
                key = _neighbor_key(nx, nz)
                nb = neighbors.get(key)
                if nb is None:
                    continue
                lx, lz = _local_coords(nx, nz)
                nb_id = nb.get_block(lx, y, lz)
                nb_level = _chunk_get_metadata(nb, lx, y, lz)
                if nb_id == 0 or (nb_id == water_id and nb_level < spread_level):
                    nb_p = neighbor_proposals.setdefault(key, {})
                    pos = (lx, y, lz)
                    nb_p[pos] = max(nb_p.get(pos, 0), spread_level)

    # Source creation: a flowing block adjacent to 2+ sources becomes a source
    for raw_x, raw_y, raw_z in np.argwhere(blocks == water_id):
        x, y, z = int(raw_x), int(raw_y), int(raw_z)
        level = int(metadata[x, y, z]) or FLUID_MAX_LEVEL
        if _is_source(level):
            continue
        source_count = 0
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb_id = get_block_nb(x + dx, y, z + dz)
            if nb_id == water_id:
                nb_lvl = get_meta_nb(x + dx, y, z + dz) or FLUID_MAX_LEVEL
                if _is_source(nb_lvl):
                    source_count += 1
        if source_count >= 2:
            proposals[(x, y, z)] = FLUID_MAX_LEVEL

    changed = 0
    for x, y, z in drain:
        if (x, y, z) not in proposals:
            chunk.set_block(x, y, z, 0)
            chunk.set_metadata(x, y, z, 0)
            changed += 1
    for (x, y, z), level in proposals.items():
        if chunk.get_block(x, y, z) != water_id:
            chunk.set_block(x, y, z, water_id)
            changed += 1
        if chunk.set_metadata(x, y, z, level):
            changed += 1

    changed_neighbor_keys: set[tuple[int, int]] = set()
    if neighbor_proposals and neighbors is not None:
        for key, nb_p in neighbor_proposals.items():
            nb = neighbors.get(key)
            if nb is None:
                continue
            nb_changed = 0
            for (lx, y, lz), level in nb_p.items():
                if nb.get_block(lx, y, lz) != water_id:
                    nb.set_block(lx, y, lz, water_id)
                    nb_changed += 1
                if nb.set_metadata(lx, y, lz, level):
                    nb_changed += 1
            if nb_changed:
                changed_neighbor_keys.add(key)

    return FluidUpdate(changed, frozenset(changed_neighbor_keys))
