"""Unit tests for the world generation pipeline (Phase 3.2)."""

from __future__ import annotations

import pytest

from voxel_sandbox.domain.biomes import load_biome_registry_from_toml
from voxel_sandbox.domain.blocks import BlockRegistry, load_block_registry_from_toml
from voxel_sandbox.engine.chunks import ChunkCoord
from voxel_sandbox.engine.gameplay_constants import (
    DUNGEON_DENSITY,
    HIGHLANDS_PILLAR_DENSITY,
    ORE_DENSITY,
    TREE_DENSITY_DEFAULT,
    TREE_DENSITY_SWAMP,
    TREE_DENSITY_WOODS,
)
from voxel_sandbox.engine.generation import (
    BiomeSurfacePlacer,
    FeatureDecorator,
    HeightProvider,
    SurfacePlacer,
    TerrainGenerator,
    WorldSeed,
)
from voxel_sandbox.engine.generation.terrain import Biome


@pytest.fixture()
def block_registry(tmp_path):
    from voxel_sandbox.app.paths import resource_path

    return load_block_registry_from_toml(resource_path("data/blocks.toml"))


@pytest.fixture()
def biome_registry(tmp_path):
    from voxel_sandbox.app.paths import resource_path

    return load_biome_registry_from_toml(resource_path("data/biomes.toml"))


# ---------------------------------------------------------------------------
# DimensionDef structural checks
# ---------------------------------------------------------------------------


def test_dimension_def_is_frozen() -> None:
    generator = TerrainGenerator(WorldSeed.parse("struct-test"))
    dim = generator._dimension
    with pytest.raises((AttributeError, TypeError)):
        dim.water_level = 99  # type: ignore[misc]


def test_dimension_has_six_decorators() -> None:
    generator = TerrainGenerator(WorldSeed.parse("decorators"))
    assert len(generator._dimension.feature_decorators) == 6


def test_generator_is_its_own_height_provider() -> None:
    generator = TerrainGenerator(WorldSeed.parse("provider"))
    assert generator._dimension.height_provider is generator


# ---------------------------------------------------------------------------
# HeightProvider protocol compliance
# ---------------------------------------------------------------------------


def test_height_provider_protocol() -> None:
    generator = TerrainGenerator(WorldSeed.parse("protocol"))
    # TerrainGenerator must satisfy HeightProvider
    provider: HeightProvider = generator
    assert isinstance(provider.height_at(0, 0), int)
    assert isinstance(provider.biome_key_at(0, 0), str)


def test_biome_key_at_returns_valid_key() -> None:
    generator = TerrainGenerator(WorldSeed.parse("biomekey"))
    valid_keys = {b.value for b in Biome}
    for x, z in [(-100, 200), (0, 0), (500, -300), (1000, 1000)]:
        key = generator.biome_key_at(x, z)
        assert key in valid_keys, f"biome_key_at({x}, {z}) returned {key!r}"


def test_biome_key_matches_biome_enum() -> None:
    generator = TerrainGenerator(WorldSeed.parse("keymatch"))
    assert generator.biome_key_at(0, 0) == generator.biome_at(0, 0).value


# ---------------------------------------------------------------------------
# BiomeSurfacePlacer
# ---------------------------------------------------------------------------


def test_biome_surface_placer_resolves_all_biomes(block_registry, biome_registry) -> None:
    placer = BiomeSurfacePlacer(block_registry, biome_registry)
    for biome in biome_registry:
        assert biome.key in placer._biome_blocks
        ids = placer._biome_blocks[biome.key]
        assert len(ids) == 3
        assert all(isinstance(i, int) for i in ids)


def test_biome_surface_placer_highland_is_stone(block_registry, biome_registry) -> None:
    placer = BiomeSurfacePlacer(block_registry, biome_registry)
    stone_id = block_registry.by_key("stone").id
    surface_id, subsurface_id, deep_id = placer._biome_blocks["dusk_highlands"]
    assert surface_id == stone_id
    assert subsurface_id == stone_id
    assert deep_id == stone_id


def test_biome_surface_placer_plains_has_grass_surface(block_registry, biome_registry) -> None:
    placer = BiomeSurfacePlacer(block_registry, biome_registry)
    grass_id = block_registry.by_key("grass").id
    surface_id, _sub, _deep = placer._biome_blocks["twilight_plains"]
    assert surface_id == grass_id


def test_biome_surface_placer_swamp_has_dirt_surface(block_registry, biome_registry) -> None:
    placer = BiomeSurfacePlacer(block_registry, biome_registry)
    dirt_id = block_registry.by_key("dirt").id
    surface_id, _sub, _deep = placer._biome_blocks["gloom_swamp"]
    assert surface_id == dirt_id


def test_generation_feature_block_ids_match_registry(block_registry: BlockRegistry) -> None:
    assert block_registry.by_key("dusk_crystal_ore").id == 6
    assert block_registry.by_key("gloam_lantern").id == 7
    assert block_registry.by_key("glowing_mushroom").id == 11
    assert block_registry.by_key("fireflies").id == 12


def test_generation_feature_densities_are_probabilities() -> None:
    for density in (
        DUNGEON_DENSITY,
        1.0 - HIGHLANDS_PILLAR_DENSITY,
        1.0 - ORE_DENSITY,
        TREE_DENSITY_DEFAULT,
        TREE_DENSITY_SWAMP,
        TREE_DENSITY_WOODS,
    ):
        assert 0.0 <= density <= 1.0


# ---------------------------------------------------------------------------
# TerrainGenerator with BiomeSurfacePlacer wired in
# ---------------------------------------------------------------------------


def test_generator_with_registries_is_deterministic(block_registry, biome_registry) -> None:
    seed = WorldSeed.parse("determinism")
    gen_a = TerrainGenerator(seed, block_registry=block_registry, biome_registry=biome_registry)
    gen_b = TerrainGenerator(seed, block_registry=block_registry, biome_registry=biome_registry)

    import numpy as np

    chunk_a = gen_a.generate_chunk(ChunkCoord(3, -2))
    chunk_b = gen_b.generate_chunk(ChunkCoord(3, -2))
    for sa, sb in zip(chunk_a.sections, chunk_b.sections, strict=True):
        assert np.array_equal(sa.blocks, sb.blocks)


def test_highland_chunk_has_stone_surface(block_registry, biome_registry) -> None:
    """Find a highlands coordinate and verify stone surface when using BiomeSurfacePlacer."""
    seed = WorldSeed.parse("highland-surface")
    generator = TerrainGenerator(seed, block_registry=block_registry, biome_registry=biome_registry)
    stone_id = block_registry.by_key("stone").id

    # Scan for a highlands column
    for chunk_x in range(-10, 10):
        for chunk_z in range(-10, 10):
            world_x = chunk_x * 16
            world_z = chunk_z * 16
            if generator.biome_key_at(world_x, world_z) == "dusk_highlands":
                chunk = generator.generate_chunk(ChunkCoord(chunk_x, chunk_z))
                height = generator.height_at(world_x, world_z)
                surface_block = chunk.get_block(0, height - 1, 0)
                assert surface_block == stone_id
                return

    pytest.skip("No dusk_highlands found in test range — seed-dependent, skip")


def test_default_generator_unchanged_surface(block_registry, biome_registry) -> None:
    """Default generator (no registries) always places grass at surface — unchanged behaviour."""
    seed = WorldSeed.parse("default-compat")
    generator = TerrainGenerator(seed)
    chunk = generator.generate_chunk(ChunkCoord(0, 0))
    height = generator.height_at(0, 0)
    assert chunk.get_block(0, height - 1, 0) == 3  # grass=3 hardcoded in _DefaultSurfacePlacer


def test_dungeon_decorator_carves_chamber_and_places_lamps() -> None:
    generator = TerrainGenerator(WorldSeed.parse("b3-generation"))
    chunk = generator.generate_chunk(ChunkCoord(-19, -13))

    assert chunk.get_block(8, 9, 8) == 0
    assert chunk.get_block(8, 12, 8) == 0
    assert chunk.get_block(6, 12, 6) == 7


def test_dusk_highlands_decorator_places_pillar_with_ore_cap() -> None:
    generator = TerrainGenerator(WorldSeed.parse("b3-generation"))
    chunk = generator.generate_chunk(ChunkCoord(-20, -12))

    local_x = 3
    local_z = 14
    top_y = generator.height_at(-317, -178)
    pillar_height = 13

    for y in range(top_y, top_y + pillar_height):
        assert chunk.get_block(local_x, y, local_z) == 1
    assert chunk.get_block(local_x, top_y + pillar_height, local_z) == 6


def test_twilight_woods_decorator_places_mushrooms_and_fireflies() -> None:
    generator = TerrainGenerator(WorldSeed.parse("b3-variety"))
    chunk = generator.generate_chunk(ChunkCoord(-30, -27))

    assert generator.biome_key_at(-471, -421) == "twilight_woods"
    assert chunk.get_block(9, 33, 11) == 11
    assert chunk.get_block(8, 45, 11) == 12


def test_gloom_swamp_decorator_places_glowing_mushrooms() -> None:
    generator = TerrainGenerator(WorldSeed.parse("b3-swamp-variety"))
    chunk = generator.generate_chunk(ChunkCoord(-40, -30))

    assert generator.biome_key_at(-635, -473) == "gloom_swamp"
    assert chunk.get_block(5, 32, 7) == 11


# ---------------------------------------------------------------------------
# Protocol runtime checks (structural typing)
# ---------------------------------------------------------------------------


def test_surface_placer_protocol_structural() -> None:
    """_DefaultSurfacePlacer satisfies SurfacePlacer protocol."""
    from voxel_sandbox.engine.generation.terrain import _DefaultSurfacePlacer

    placer = _DefaultSurfacePlacer()
    assert isinstance(placer, SurfacePlacer)


def test_feature_decorator_protocol_structural() -> None:
    """All feature decorators satisfy FeatureDecorator protocol."""
    from voxel_sandbox.engine.generation.terrain import (
        _CaveDecorator,
        _DungeonDecorator,
        _HighlandsFeatureDecorator,
        _OreDecorator,
        _TreeDecorator,
    )

    seed = WorldSeed.parse("proto")
    for cls in (
        _CaveDecorator,
        _OreDecorator,
        _TreeDecorator,
        _DungeonDecorator,
        _HighlandsFeatureDecorator,
    ):
        assert isinstance(cls(seed), FeatureDecorator)
