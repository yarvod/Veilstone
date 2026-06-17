from __future__ import annotations

import math
from enum import Enum
from pathlib import Path

import numpy as np

from voxel_sandbox.engine.chunks import SECTION_SIZE, Chunk, ChunkCoord, DirtyFlag
from voxel_sandbox.engine.generation.seed import WorldSeed
from voxel_sandbox.engine.generation.structures import (
    StructureTemplate,
    load_structure_templates,
    structure_placements_for_chunk,
)


class Biome(Enum):
    TWILIGHT_PLAINS = "twilight_plains"
    TWILIGHT_WOODS = "twilight_woods"
    GLOOM_SWAMP = "gloom_swamp"
    DUSK_HIGHLANDS = "dusk_highlands"


class TerrainGenerator:
    WATER_LEVEL = 32

    def __init__(self, seed: WorldSeed) -> None:
        self.seed = seed
        self.structure_templates: tuple[StructureTemplate, ...] = load_structure_templates(
            Path(__file__).parent / "structure_templates"
        )

    def height_at(self, world_x: int, world_z: int) -> int:
        broad = self._value_noise(world_x / 128.0, world_z / 128.0, 0)
        detail = self._value_noise(world_x / 32.0, world_z / 32.0, 1)
        # Twilight Forest: mostly flat, occasionally dropping below water level (32) for pools/swamps
        hill_factor = broad * broad * broad
        return 25 + int(hill_factor * 30.0 + detail * 10.0)

    def biome_at(self, world_x: int, world_z: int) -> Biome:
        temperature = self._value_noise(world_x / 96.0, world_z / 96.0, 2)
        moisture = self._value_noise(world_x / 96.0, world_z / 96.0, 3)
        if temperature < 0.32:
            return Biome.DUSK_HIGHLANDS
        if moisture > 0.68:
            return Biome.GLOOM_SWAMP
        if moisture > 0.46:
            return Biome.TWILIGHT_WOODS
        return Biome.TWILIGHT_PLAINS

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
                if height < self.WATER_LEVEL:
                    self._fill_water_column(
                        chunk,
                        local_x,
                        local_z,
                        height,
                        self.WATER_LEVEL,
                        touched_sections,
                    )
        self._carve_caves(chunk, coord, touched_sections)
        self._place_ores(chunk, coord, touched_sections)
        self._place_trees(chunk, coord, touched_sections)
        self._place_structures(chunk, coord, touched_sections)
        for section_index in touched_sections:
            section = chunk.sections[section_index]
            section.dirty = DirtyFlag.MESH | DirtyFlag.LIGHTING | DirtyFlag.SAVE
            section.revision = 1
        return chunk

    def _place_structures(
        self,
        chunk: Chunk,
        coord: ChunkCoord,
        touched_sections: set[int],
    ) -> None:
        for placement in structure_placements_for_chunk(
            coord,
            self.seed,
            self.structure_templates,
            self.height_at,
        ):
            origin_x, origin_y, origin_z = placement.origin
            for block in placement.template.blocks:
                self._set_if_inside(
                    chunk,
                    coord,
                    origin_x + block.x,
                    origin_y + block.y,
                    origin_z + block.z,
                    block.block_id,
                    touched_sections,
                )

    def _carve_caves(
        self,
        chunk: Chunk,
        coord: ChunkCoord,
        touched_sections: set[int],
    ) -> None:
        seed_phase = (self.seed.value & 0xFFFF) / 65535.0 * math.tau
        for section_index, section in enumerate(chunk.sections[:3]):
            world_y = section_index * SECTION_SIZE + np.arange(SECTION_SIZE)[None, :, None]
            world_x = coord.x * SECTION_SIZE + np.arange(SECTION_SIZE)[:, None, None]
            world_z = coord.z * SECTION_SIZE + np.arange(SECTION_SIZE)[None, None, :]
            cave_field = (
                np.sin(world_x * 0.17 + seed_phase)
                + np.sin(world_y * 0.23 + seed_phase * 1.7)
                + np.cos(world_z * 0.19 - seed_phase * 0.6)
                + np.sin((world_x + world_z) * 0.09 + seed_phase * 2.3)
            )
            mask = (cave_field > 3.12) & (world_y > 4) & (section.blocks != 0)
            if np.any(mask):
                section.blocks[mask] = 0
                touched_sections.add(section_index)

    def _place_ores(
        self,
        chunk: Chunk,
        coord: ChunkCoord,
        touched_sections: set[int],
    ) -> None:
        for section_index, section in enumerate(chunk.sections[:2]):
            for x, y, z in np.argwhere(section.blocks == 1):
                world_x = coord.x * SECTION_SIZE + int(x)
                world_y = section_index * SECTION_SIZE + int(y)
                world_z = coord.z * SECTION_SIZE + int(z)
                if self._hash3(world_x, world_y, world_z, 10) > 0.988:
                    section.blocks[x, y, z] = 6
                    touched_sections.add(section_index)

    def _place_trees(
        self,
        chunk: Chunk,
        coord: ChunkCoord,
        touched_sections: set[int],
    ) -> None:
        min_x = coord.x * SECTION_SIZE
        min_z = coord.z * SECTION_SIZE
        for world_x in range(min_x - 2, min_x + SECTION_SIZE + 2):
            for world_z in range(min_z - 2, min_z + SECTION_SIZE + 2):
                biome = self.biome_at(world_x, world_z)
                if self.height_at(world_x, world_z) < self.WATER_LEVEL:
                    continue
                threshold = 0.982 if biome is Biome.TWILIGHT_WOODS else 0.994
                if biome is Biome.GLOOM_SWAMP:
                    threshold = 0.989
                if self._hash3(world_x, 0, world_z, 20) <= threshold:
                    continue
                ground_y = self.height_at(world_x, world_z) - 1
                is_giant = self._hash3(world_x, 2, world_z, 25) > 0.85
                if is_giant:
                    self._place_giant_tree(chunk, coord, world_x, ground_y, world_z, touched_sections)
                else:
                    trunk_height = 4 + int(self._hash3(world_x, 1, world_z, 21) * 3)
                    for y in range(ground_y + 1, ground_y + trunk_height + 1):
                        self._set_if_inside(chunk, coord, world_x, y, world_z, 4, touched_sections)
                    crown_y = ground_y + trunk_height
                    for dx in range(-2, 3):
                        for dy in range(-1, 3):
                            for dz in range(-2, 3):
                                if abs(dx) + abs(dz) + max(0, abs(dy) - 1) > 4:
                                    continue
                                self._set_if_inside(
                                    chunk,
                                    coord,
                                    world_x + dx,
                                    crown_y + dy,
                                    world_z + dz,
                                    5,
                                    touched_sections,
                                    replace_air_only=True,
                                )
                    self._set_if_inside(chunk, coord, world_x, crown_y, world_z, 4, touched_sections)

    def _place_giant_tree(
        self,
        chunk: Chunk,
        coord: ChunkCoord,
        world_x: int,
        ground_y: int,
        world_z: int,
        touched_sections: set[int],
    ) -> None:
        trunk_height = 10 + int(self._hash3(world_x, 1, world_z, 21) * 8)
        for dx in (0, 1):
            for dz in (0, 1):
                for y in range(ground_y + 1, ground_y + trunk_height + 1):
                    self._set_if_inside(chunk, coord, world_x + dx, y, world_z + dz, 4, touched_sections)
        
        crown_y = ground_y + trunk_height
        for dx in range(-4, 6):
            for dy in range(-3, 4):
                for dz in range(-4, 6):
                    dist = math.sqrt((dx - 0.5)**2 + (dy * 1.5)**2 + (dz - 0.5)**2)
                    if dist <= 4.5 + self._hash3(world_x + dx, crown_y + dy, world_z + dz, 30) * 1.5:
                        self._set_if_inside(
                            chunk,
                            coord,
                            world_x + dx,
                            crown_y + dy,
                            world_z + dz,
                            5,
                            touched_sections,
                            replace_air_only=True,
                        )
                        if dy < 0 and self._hash3(world_x + dx, crown_y + dy, world_z + dz, 40) < 0.08:
                            self._set_if_inside(
                                chunk,
                                coord,
                                world_x + dx,
                                crown_y + dy - 1,
                                world_z + dz,
                                12,  # fireflies
                                touched_sections,
                                replace_air_only=True,
                            )
        for dx in range(-2, 4):
            for dz in range(-2, 4):
                if max(abs(dx - 0.5), abs(dz - 0.5)) > 1.0:
                    if self._hash3(world_x + dx, ground_y + 1, world_z + dz, 50) < 0.15:
                        self._set_if_inside(
                            chunk,
                            coord,
                            world_x + dx,
                            ground_y + 1,
                            world_z + dz,
                            11,  # glowing mushroom
                            touched_sections,
                            replace_air_only=True,
                        )

    @staticmethod
    def _set_if_inside(
        chunk: Chunk,
        coord: ChunkCoord,
        world_x: int,
        world_y: int,
        world_z: int,
        block_id: int,
        touched_sections: set[int],
        *,
        replace_air_only: bool = False,
    ) -> None:
        local_x = world_x - coord.x * SECTION_SIZE
        local_z = world_z - coord.z * SECTION_SIZE
        if not (0 <= local_x < SECTION_SIZE and 0 <= local_z < SECTION_SIZE and 0 <= world_y < 128):
            return
        section_index, local_y = divmod(world_y, SECTION_SIZE)
        section = chunk.sections[section_index]
        if replace_air_only and int(section.blocks[local_x, local_y, local_z]) != 0:
            return
        section.blocks[local_x, local_y, local_z] = block_id
        touched_sections.add(section_index)

    @staticmethod
    def _fill_water_column(
        chunk: Chunk,
        x: int,
        z: int,
        start_y: int,
        end_y: int,
        touched_sections: set[int],
    ) -> None:
        for y in range(start_y, end_y):
            section_index, local_y = divmod(y, SECTION_SIZE)
            section = chunk.sections[section_index]
            section.blocks[x, local_y, z] = 8
            section.metadata[x, local_y, z] = 8
            touched_sections.add(section_index)

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

    def _hash3(self, x: int, y: int, z: int, channel: int) -> float:
        value = self.seed.value ^ ((y * 0xD6E8FEB86659FD93) & 0xFFFFFFFFFFFFFFFF)
        value ^= (x * 0x9E3779B185EBCA87) & 0xFFFFFFFFFFFFFFFF
        value ^= (z * 0xC2B2AE3D27D4EB4F) & 0xFFFFFFFFFFFFFFFF
        value ^= channel * 0x165667B19E3779F9
        value ^= value >> 30
        value = (value * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
        value ^= value >> 27
        return (value & 0xFFFFFFFF) / 0xFFFFFFFF


def _smooth(value: float) -> float:
    return value * value * (3.0 - 2.0 * value)


def _lerp(start: float, end: float, amount: float) -> float:
    return start + (end - start) * amount
