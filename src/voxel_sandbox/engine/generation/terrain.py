from __future__ import annotations

import math
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from voxel_sandbox.engine.chunks import SECTION_SIZE, Chunk, ChunkCoord, DirtyFlag
from voxel_sandbox.engine.gameplay_constants import (
    DUNGEON_DENSITY,
    GROUND_COVER_DENSITY_PLAINS,
    GROUND_COVER_DENSITY_SWAMP,
    GROUND_COVER_DENSITY_WOODS,
    HIGHLANDS_PILLAR_DENSITY,
    ORE_DENSITY,
    TERRAIN_BASE_HEIGHT,
    TERRAIN_DETAIL_SCALE,
    TERRAIN_HILL_SCALE,
    TREE_DENSITY_DEFAULT,
    TREE_DENSITY_SWAMP,
    TREE_DENSITY_WOODS,
    WILDFLOWER_DENSITY_PLAINS,
    WILDFLOWER_DENSITY_WOODS,
)
from voxel_sandbox.engine.generation.pipeline import DimensionDef, HeightProvider
from voxel_sandbox.engine.generation.seed import WorldSeed
from voxel_sandbox.engine.generation.structures import (
    StructureTemplate,
    load_structure_templates,
    structure_placements_for_chunk,
)

if TYPE_CHECKING:
    from voxel_sandbox.domain.biomes import BiomeRegistry
    from voxel_sandbox.domain.blocks import BlockRegistry


class Biome(Enum):
    TWILIGHT_PLAINS = "twilight_plains"
    TWILIGHT_WOODS = "twilight_woods"
    GLOOM_SWAMP = "gloom_swamp"
    DUSK_HIGHLANDS = "dusk_highlands"


# ---------------------------------------------------------------------------
# Pure noise helpers (module-level so decorators can share them)
# ---------------------------------------------------------------------------


def _smooth(value: float) -> float:
    return value * value * (3.0 - 2.0 * value)


def _lerp(start: float, end: float, amount: float) -> float:
    return start + (end - start) * amount


def _hash(seed_value: int, x: int, z: int, channel: int) -> float:
    value = seed_value
    value ^= (x * 0x9E3779B185EBCA87) & 0xFFFFFFFFFFFFFFFF
    value ^= (z * 0xC2B2AE3D27D4EB4F) & 0xFFFFFFFFFFFFFFFF
    value ^= channel * 0x165667B19E3779F9
    value ^= value >> 30
    value = (value * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
    value ^= value >> 27
    value = (value * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
    value ^= value >> 31
    return (value & 0xFFFFFFFF) / 0xFFFFFFFF


def _hash3(seed_value: int, x: int, y: int, z: int, channel: int) -> float:
    value = seed_value ^ ((y * 0xD6E8FEB86659FD93) & 0xFFFFFFFFFFFFFFFF)
    value ^= (x * 0x9E3779B185EBCA87) & 0xFFFFFFFFFFFFFFFF
    value ^= (z * 0xC2B2AE3D27D4EB4F) & 0xFFFFFFFFFFFFFFFF
    value ^= channel * 0x165667B19E3779F9
    value ^= value >> 30
    value = (value * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
    value ^= value >> 27
    return (value & 0xFFFFFFFF) / 0xFFFFFFFF


def _value_noise(seed_value: int, x: float, z: float, channel: int) -> float:
    x0, z0 = math.floor(x), math.floor(z)
    tx, tz = _smooth(x - x0), _smooth(z - z0)
    a = _lerp(_hash(seed_value, x0, z0, channel), _hash(seed_value, x0 + 1, z0, channel), tx)
    b = _lerp(
        _hash(seed_value, x0, z0 + 1, channel),
        _hash(seed_value, x0 + 1, z0 + 1, channel),
        tx,
    )
    return _lerp(a, b, tz)


# ---------------------------------------------------------------------------
# Column helpers (module-level, shared by placers)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Surface placers
# ---------------------------------------------------------------------------


class _DefaultSurfacePlacer:
    """Hardcoded layering: stone=1, dirt=2, grass=3, water=8."""

    def fill_column(
        self,
        chunk: Chunk,
        coord: ChunkCoord,
        local_x: int,
        local_z: int,
        height: int,
        water_level: int,
        height_provider: HeightProvider,
        touched_sections: set[int],
    ) -> None:
        stone_end = max(1, height - 3)
        _fill_column(chunk, local_x, local_z, 0, stone_end, 1, touched_sections)
        _fill_column(chunk, local_x, local_z, stone_end, height - 1, 2, touched_sections)
        _fill_column(chunk, local_x, local_z, height - 1, height, 3, touched_sections)
        if height < water_level:
            _fill_water_column(chunk, local_x, local_z, height, water_level, touched_sections)


class BiomeSurfacePlacer:
    """Data-driven surface placer — reads block IDs from BlockRegistry + BiomeDef."""

    def __init__(self, block_registry: BlockRegistry, biome_registry: BiomeRegistry) -> None:
        # Pre-resolve biome key → (surface_id, subsurface_id, deep_id)
        self._biome_blocks: dict[str, tuple[int, int, int]] = {}
        for biome in biome_registry:
            self._biome_blocks[biome.key] = (
                block_registry.by_key(biome.surface_block).id,
                block_registry.by_key(biome.subsurface_block).id,
                block_registry.by_key(biome.deep_block).id,
            )

    def fill_column(
        self,
        chunk: Chunk,
        coord: ChunkCoord,
        local_x: int,
        local_z: int,
        height: int,
        water_level: int,
        height_provider: HeightProvider,
        touched_sections: set[int],
    ) -> None:
        world_x = coord.x * SECTION_SIZE + local_x
        world_z = coord.z * SECTION_SIZE + local_z
        biome_key = height_provider.biome_key_at(world_x, world_z)
        surface_id, subsurface_id, deep_id = self._biome_blocks.get(
            biome_key,
            (3, 2, 1),  # fallback: grass, dirt, stone
        )
        stone_end = max(1, height - 3)
        _fill_column(chunk, local_x, local_z, 0, stone_end, deep_id, touched_sections)
        _fill_column(
            chunk, local_x, local_z, stone_end, height - 1, subsurface_id, touched_sections
        )
        _fill_column(chunk, local_x, local_z, height - 1, height, surface_id, touched_sections)
        if height < water_level:
            _fill_water_column(chunk, local_x, local_z, height, water_level, touched_sections)


# ---------------------------------------------------------------------------
# Feature decorators
# ---------------------------------------------------------------------------


class _CaveDecorator:
    def __init__(self, seed: WorldSeed) -> None:
        self._seed_phase = (seed.value & 0xFFFF) / 65535.0 * math.tau

    def decorate(
        self,
        chunk: Chunk,
        coord: ChunkCoord,
        height_provider: HeightProvider,
        touched_sections: set[int],
    ) -> None:
        seed_phase = self._seed_phase
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


class _OreDecorator:
    def __init__(self, seed: WorldSeed) -> None:
        self._seed_value = seed.value

    def decorate(
        self,
        chunk: Chunk,
        coord: ChunkCoord,
        height_provider: HeightProvider,
        touched_sections: set[int],
    ) -> None:
        seed_value = self._seed_value
        for section_index, section in enumerate(chunk.sections[:2]):
            for x, y, z in np.argwhere(section.blocks == 1):
                world_x = coord.x * SECTION_SIZE + int(x)
                world_y = section_index * SECTION_SIZE + int(y)
                world_z = coord.z * SECTION_SIZE + int(z)
                if _hash3(seed_value, world_x, world_y, world_z, 10) > ORE_DENSITY:
                    section.blocks[x, y, z] = 6
                    touched_sections.add(section_index)


class _TreeDecorator:
    def __init__(self, seed: WorldSeed) -> None:
        self._seed_value = seed.value

    def decorate(
        self,
        chunk: Chunk,
        coord: ChunkCoord,
        height_provider: HeightProvider,
        touched_sections: set[int],
    ) -> None:
        seed_value = self._seed_value
        min_x = coord.x * SECTION_SIZE
        min_z = coord.z * SECTION_SIZE
        for world_x in range(min_x - 2, min_x + SECTION_SIZE + 2):
            for world_z in range(min_z - 2, min_z + SECTION_SIZE + 2):
                biome_key = height_provider.biome_key_at(world_x, world_z)
                if height_provider.height_at(world_x, world_z) < TerrainGenerator.WATER_LEVEL:
                    continue
                if biome_key == "twilight_woods":
                    threshold = TREE_DENSITY_WOODS
                elif biome_key == "gloom_swamp":
                    threshold = TREE_DENSITY_SWAMP
                else:
                    threshold = TREE_DENSITY_DEFAULT
                if _hash3(seed_value, world_x, 0, world_z, 20) <= threshold:
                    continue
                ground_y = height_provider.height_at(world_x, world_z) - 1
                is_giant = _hash3(seed_value, world_x, 2, world_z, 25) > 0.85
                if is_giant:
                    self._place_giant_tree(
                        chunk, coord, world_x, ground_y, world_z, seed_value, touched_sections
                    )
                else:
                    trunk_height = 4 + int(_hash3(seed_value, world_x, 1, world_z, 21) * 3)
                    for y in range(ground_y + 1, ground_y + trunk_height + 1):
                        _set_if_inside(chunk, coord, world_x, y, world_z, 4, touched_sections)
                    crown_y = ground_y + trunk_height
                    for dx in range(-2, 3):
                        for dy in range(-1, 3):
                            for dz in range(-2, 3):
                                if abs(dx) + abs(dz) + max(0, abs(dy) - 1) > 4:
                                    continue
                                _set_if_inside(
                                    chunk,
                                    coord,
                                    world_x + dx,
                                    crown_y + dy,
                                    world_z + dz,
                                    5,
                                    touched_sections,
                                    replace_air_only=True,
                                )
                    _set_if_inside(chunk, coord, world_x, crown_y, world_z, 4, touched_sections)

    @staticmethod
    def _place_giant_tree(
        chunk: Chunk,
        coord: ChunkCoord,
        world_x: int,
        ground_y: int,
        world_z: int,
        seed_value: int,
        touched_sections: set[int],
    ) -> None:
        trunk_height = 10 + int(_hash3(seed_value, world_x, 1, world_z, 21) * 8)
        for dx in (0, 1):
            for dz in (0, 1):
                for y in range(ground_y + 1, ground_y + trunk_height + 1):
                    _set_if_inside(chunk, coord, world_x + dx, y, world_z + dz, 4, touched_sections)

        crown_y = ground_y + trunk_height
        for dx in range(-4, 6):
            for dy in range(-3, 4):
                for dz in range(-4, 6):
                    dist = math.sqrt((dx - 0.5) ** 2 + (dy * 1.5) ** 2 + (dz - 0.5) ** 2)
                    jitter = _hash3(seed_value, world_x + dx, crown_y + dy, world_z + dz, 30)
                    if dist <= 4.5 + jitter * 1.5:
                        _set_if_inside(
                            chunk,
                            coord,
                            world_x + dx,
                            crown_y + dy,
                            world_z + dz,
                            5,
                            touched_sections,
                            replace_air_only=True,
                        )
                        firefly_r = _hash3(seed_value, world_x + dx, crown_y + dy, world_z + dz, 40)
                        if dy < 0 and firefly_r < 0.08:
                            _set_if_inside(
                                chunk,
                                coord,
                                world_x + dx,
                                crown_y + dy - 1,
                                world_z + dz,
                                12,
                                touched_sections,
                                replace_air_only=True,
                            )
        for dx in range(-2, 4):
            for dz in range(-2, 4):
                if (
                    max(abs(dx - 0.5), abs(dz - 0.5)) > 1.0
                    and _hash3(seed_value, world_x + dx, ground_y + 1, world_z + dz, 50) < 0.15
                ):
                    _set_if_inside(
                        chunk,
                        coord,
                        world_x + dx,
                        ground_y + 1,
                        world_z + dz,
                        11,
                        touched_sections,
                        replace_air_only=True,
                    )


class _GroundCoverDecorator:
    def __init__(self, seed: WorldSeed) -> None:
        self._seed_value = seed.value

    def decorate(
        self,
        chunk: Chunk,
        coord: ChunkCoord,
        height_provider: HeightProvider,
        touched_sections: set[int],
    ) -> None:
        min_x = coord.x * SECTION_SIZE
        min_z = coord.z * SECTION_SIZE
        for world_x in range(min_x, min_x + SECTION_SIZE):
            for world_z in range(min_z, min_z + SECTION_SIZE):
                biome_key = height_provider.biome_key_at(world_x, world_z)
                density, flower_density = _ground_cover_density(biome_key)
                if density <= 0.0:
                    continue
                height = height_provider.height_at(world_x, world_z)
                if height <= TerrainGenerator.WATER_LEVEL:
                    continue
                cover_roll = _hash3(self._seed_value, world_x, height, world_z, 82)
                if cover_roll >= density:
                    continue
                flower_roll = _hash3(self._seed_value, world_x, height, world_z, 83)
                block_id = 14 if flower_roll < flower_density else 13
                _set_if_inside(
                    chunk,
                    coord,
                    world_x,
                    height,
                    world_z,
                    block_id,
                    touched_sections,
                    replace_air_only=True,
                )


def _ground_cover_density(biome_key: str) -> tuple[float, float]:
    if biome_key == Biome.TWILIGHT_WOODS.value:
        return GROUND_COVER_DENSITY_WOODS, WILDFLOWER_DENSITY_WOODS
    if biome_key == Biome.TWILIGHT_PLAINS.value:
        return GROUND_COVER_DENSITY_PLAINS, WILDFLOWER_DENSITY_PLAINS
    if biome_key == Biome.GLOOM_SWAMP.value:
        return GROUND_COVER_DENSITY_SWAMP, 0.0
    return 0.0, 0.0


class _DungeonDecorator:
    """Places one carved underground chamber per qualifying chunk."""

    def __init__(self, seed: WorldSeed) -> None:
        self._seed_value = seed.value

    def decorate(
        self,
        chunk: Chunk,
        coord: ChunkCoord,
        height_provider: HeightProvider,
        touched_sections: set[int],
    ) -> None:
        if _hash(self._seed_value, coord.x, coord.z, 60) > DUNGEON_DENSITY:
            return
        room_x = coord.x * SECTION_SIZE + 8
        room_y = 8  # floor at room_y; interior y = room_y+1 .. room_y+4
        room_z = coord.z * SECTION_SIZE + 8
        for dx in range(-3, 4):
            for dy in range(1, 5):
                for dz in range(-3, 4):
                    _set_if_inside(
                        chunk, coord, room_x + dx, room_y + dy, room_z + dz, 0, touched_sections
                    )
        for lx, lz in ((-2, -2), (2, -2), (-2, 2), (2, 2)):
            _set_if_inside(chunk, coord, room_x + lx, room_y + 4, room_z + lz, 7, touched_sections)
        for sy in range(room_y + 5, room_y + 15):
            for dx in range(-1, 2):
                for dz in range(-1, 2):
                    _set_if_inside(chunk, coord, room_x + dx, sy, room_z + dz, 0, touched_sections)


class _HighlandsFeatureDecorator:
    """Raises stone pillars capped with ore in Dusk Highlands columns."""

    def __init__(self, seed: WorldSeed) -> None:
        self._seed_value = seed.value

    def decorate(
        self,
        chunk: Chunk,
        coord: ChunkCoord,
        height_provider: HeightProvider,
        touched_sections: set[int],
    ) -> None:
        seed_value = self._seed_value
        min_x = coord.x * SECTION_SIZE
        min_z = coord.z * SECTION_SIZE
        for world_x in range(min_x, min_x + SECTION_SIZE):
            for world_z in range(min_z, min_z + SECTION_SIZE):
                if height_provider.biome_key_at(world_x, world_z) != Biome.DUSK_HIGHLANDS.value:
                    continue
                if _hash3(seed_value, world_x, 0, world_z, 70) < HIGHLANDS_PILLAR_DENSITY:
                    continue
                top_y = height_provider.height_at(world_x, world_z)
                pillar_h = 5 + int(_hash3(seed_value, world_x, 1, world_z, 71) * 10)
                for y in range(top_y, top_y + pillar_h):
                    _set_if_inside(chunk, coord, world_x, y, world_z, 1, touched_sections)
                _set_if_inside(
                    chunk, coord, world_x, top_y + pillar_h, world_z, 6, touched_sections
                )


class _StructureDecorator:
    def __init__(self, seed: WorldSeed, templates: tuple[StructureTemplate, ...]) -> None:
        self._seed = seed
        self._templates = templates

    def decorate(
        self,
        chunk: Chunk,
        coord: ChunkCoord,
        height_provider: HeightProvider,
        touched_sections: set[int],
    ) -> None:
        for placement in structure_placements_for_chunk(
            coord,
            self._seed,
            self._templates,
            height_provider.height_at,
        ):
            origin_x, origin_y, origin_z = placement.origin
            for block in placement.template.blocks:
                _set_if_inside(
                    chunk,
                    coord,
                    origin_x + block.x,
                    origin_y + block.y,
                    origin_z + block.z,
                    block.block_id,
                    touched_sections,
                )


# ---------------------------------------------------------------------------
# TerrainGenerator — orchestrator
# ---------------------------------------------------------------------------


class TerrainGenerator:
    WATER_LEVEL = 32

    def __init__(
        self,
        seed: WorldSeed,
        *,
        block_registry: BlockRegistry | None = None,
        biome_registry: BiomeRegistry | None = None,
    ) -> None:
        self.seed = seed
        self.structure_templates: tuple[StructureTemplate, ...] = load_structure_templates(
            Path(__file__).parent / "structure_templates"
        )
        # Biome-specific base and hill amplitude make distant silhouettes readable.
        self._biome_base_height: dict[str, int] = {}
        self._biome_hill_scale: dict[str, float] = {}
        if biome_registry is not None:
            for biome in biome_registry:
                self._biome_base_height[biome.key] = biome.base_height
                self._biome_hill_scale[biome.key] = biome.height_variation * 2.0

        surface_placer: _DefaultSurfacePlacer | BiomeSurfacePlacer
        if block_registry is not None and biome_registry is not None:
            surface_placer = BiomeSurfacePlacer(block_registry, biome_registry)
        else:
            surface_placer = _DefaultSurfacePlacer()

        self._dimension = DimensionDef(
            water_level=self.WATER_LEVEL,
            height_provider=self,
            surface_placer=surface_placer,
            feature_decorators=(
                _CaveDecorator(seed),
                _OreDecorator(seed),
                _TreeDecorator(seed),
                _GroundCoverDecorator(seed),
                _DungeonDecorator(seed),
                _HighlandsFeatureDecorator(seed),
                _StructureDecorator(seed, self.structure_templates),
            ),
        )

    def height_at(self, world_x: int, world_z: int) -> int:
        broad = _value_noise(self.seed.value, world_x / 128.0, world_z / 128.0, 0)
        detail = _value_noise(self.seed.value, world_x / 32.0, world_z / 32.0, 1)
        hill_factor = broad * broad * broad
        biome_key = self.biome_key_at(world_x, world_z)
        base_height = self._biome_base_height.get(biome_key, TERRAIN_BASE_HEIGHT)
        hill_scale = self._biome_hill_scale.get(biome_key, TERRAIN_HILL_SCALE)
        return base_height + int(hill_factor * hill_scale + detail * TERRAIN_DETAIL_SCALE)

    def biome_key_at(self, world_x: int, world_z: int) -> str:
        temperature = _value_noise(self.seed.value, world_x / 96.0, world_z / 96.0, 2)
        moisture = _value_noise(self.seed.value, world_x / 96.0, world_z / 96.0, 3)
        if temperature < 0.32:
            return Biome.DUSK_HIGHLANDS.value
        if moisture > 0.68:
            return Biome.GLOOM_SWAMP.value
        if moisture > 0.46:
            return Biome.TWILIGHT_WOODS.value
        return Biome.TWILIGHT_PLAINS.value

    def biome_at(self, world_x: int, world_z: int) -> Biome:
        return Biome(self.biome_key_at(world_x, world_z))

    def generate_chunk(self, coord: ChunkCoord) -> Chunk:
        chunk = Chunk(coord)
        touched_sections: set[int] = set()
        dim = self._dimension

        for local_x in range(SECTION_SIZE):
            for local_z in range(SECTION_SIZE):
                world_x = coord.x * SECTION_SIZE + local_x
                world_z = coord.z * SECTION_SIZE + local_z
                height = dim.height_provider.height_at(world_x, world_z)
                dim.surface_placer.fill_column(
                    chunk,
                    coord,
                    local_x,
                    local_z,
                    height,
                    dim.water_level,
                    dim.height_provider,
                    touched_sections,
                )

        for decorator in dim.feature_decorators:
            decorator.decorate(chunk, coord, dim.height_provider, touched_sections)

        for section_index in touched_sections:
            section = chunk.sections[section_index]
            section.dirty = DirtyFlag.MESH | DirtyFlag.LIGHTING | DirtyFlag.SAVE
            section.revision = 1
        return chunk
