from __future__ import annotations

import math
from enum import Enum

from voxel_sandbox.engine.chunks import SECTION_SIZE, Chunk, ChunkCoord, DirtyFlag
from voxel_sandbox.engine.generation.seed import WorldSeed


class Biome(Enum):
    CALM_PLAINS = "calm_plains"
    OLD_FOREST = "old_forest"
    ASH_SWAMP = "ash_swamp"
    MOONLIT_HIGHLANDS = "moonlit_highlands"


class TerrainGenerator:
    def __init__(self, seed: WorldSeed) -> None:
        self.seed = seed

    def height_at(self, world_x: int, world_z: int) -> int:
        broad = self._value_noise(world_x / 64.0, world_z / 64.0, 0)
        detail = self._value_noise(world_x / 20.0, world_z / 20.0, 1)
        return 24 + int(broad * 18.0 + detail * 7.0)

    def biome_at(self, world_x: int, world_z: int) -> Biome:
        temperature = self._value_noise(world_x / 96.0, world_z / 96.0, 2)
        moisture = self._value_noise(world_x / 96.0, world_z / 96.0, 3)
        if temperature < 0.32:
            return Biome.MOONLIT_HIGHLANDS
        if moisture > 0.68:
            return Biome.ASH_SWAMP
        if moisture > 0.46:
            return Biome.OLD_FOREST
        return Biome.CALM_PLAINS

    def generate_chunk(self, coord: ChunkCoord) -> Chunk:
        chunk = Chunk(coord)
        touched_sections: set[int] = set()
        for local_x in range(SECTION_SIZE):
            for local_z in range(SECTION_SIZE):
                world_x = coord.x * SECTION_SIZE + local_x
                world_z = coord.z * SECTION_SIZE + local_z
                height = self.height_at(world_x, world_z)
                stone_end = max(1, height - 3)
                self._fill_column(chunk, local_x, local_z, 0, stone_end, 1, touched_sections)
                self._fill_column(
                    chunk, local_x, local_z, stone_end, height - 1, 2, touched_sections
                )
                self._fill_column(chunk, local_x, local_z, height - 1, height, 3, touched_sections)
        for section_index in touched_sections:
            section = chunk.sections[section_index]
            section.dirty = DirtyFlag.MESH | DirtyFlag.LIGHTING | DirtyFlag.SAVE
            section.revision = 1
        return chunk

    @staticmethod
    def _fill_column(
        chunk: Chunk,
        x: int,
        z: int,
        start_y: int,
        end_y: int,
        block_id: int,
        touched_sections: set[int],
    ) -> None:
        cursor = start_y
        while cursor < end_y:
            section_index, local_y = divmod(cursor, SECTION_SIZE)
            count = min(end_y - cursor, SECTION_SIZE - local_y)
            chunk.sections[section_index].blocks[x, local_y : local_y + count, z] = block_id
            touched_sections.add(section_index)
            cursor += count

    def _value_noise(self, x: float, z: float, channel: int) -> float:
        x0, z0 = math.floor(x), math.floor(z)
        tx, tz = _smooth(x - x0), _smooth(z - z0)
        a = _lerp(self._hash(x0, z0, channel), self._hash(x0 + 1, z0, channel), tx)
        b = _lerp(self._hash(x0, z0 + 1, channel), self._hash(x0 + 1, z0 + 1, channel), tx)
        return _lerp(a, b, tz)

    def _hash(self, x: int, z: int, channel: int) -> float:
        value = self.seed.value
        value ^= (x * 0x9E3779B185EBCA87) & 0xFFFFFFFFFFFFFFFF
        value ^= (z * 0xC2B2AE3D27D4EB4F) & 0xFFFFFFFFFFFFFFFF
        value ^= channel * 0x165667B19E3779F9
        value ^= value >> 30
        value = (value * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
        value ^= value >> 27
        value = (value * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
        value ^= value >> 31
        return (value & 0xFFFFFFFF) / 0xFFFFFFFF


def _smooth(value: float) -> float:
    return value * value * (3.0 - 2.0 * value)


def _lerp(start: float, end: float, amount: float) -> float:
    return start + (end - start) * amount
