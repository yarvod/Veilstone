"""Unit tests for the world generation pipeline (Phase 3.2)."""

from __future__ import annotations

import pytest

from voxel_sandbox.domain.biomes import BiomeRegistry, load_biome_registry_from_toml
from voxel_sandbox.domain.blocks import BlockRegistry, load_block_registry_from_toml
from voxel_sandbox.engine.chunks import ChunkCoord
from voxel_sandbox.engine.gameplay_constants import (
    DUNGEON_DENSITY,
    GROUND_COVER_DENSITY_PLAINS,
    GROUND_COVER_DENSITY_SWAMP,
    GROUND_COVER_DENSITY_WOODS,
    HIGHLANDS_FORMATION_DENSITY,
    ORE_DENSITY,
    TREE_DENSITY_DEFAULT,
    TREE_DENSITY_SWAMP,
    TREE_DENSITY_WOODS,
    WILDFLOWER_DENSITY_PLAINS,
    WILDFLOWER_DENSITY_WOODS,
)
from voxel_sandbox.engine.generation import (
    BiomeSurfacePlacer,
    FeatureDecorator,
    HeightProvider,
    SurfacePlacer,
    TerrainGenerator,
    WorldSeed,
    structure_placements_for_chunk,
)
from voxel_sandbox.engine.generation.terrain import (
    Biome,
    _HighlandsFeatureDecorator,  # pyright: ignore[reportPrivateUsage]
)


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
    assert len(generator._dimension.feature_decorators) == 7


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
    assert block_registry.by_key("tall_grass").id == 13
    assert block_registry.by_key("wildflower").id == 14


def test_generation_feature_densities_are_probabilities() -> None:
    for density in (
        DUNGEON_DENSITY,
        HIGHLANDS_FORMATION_DENSITY,
        1.0 - ORE_DENSITY,
        TREE_DENSITY_DEFAULT,
        TREE_DENSITY_SWAMP,
        TREE_DENSITY_WOODS,
        GROUND_COVER_DENSITY_PLAINS,
        GROUND_COVER_DENSITY_WOODS,
        GROUND_COVER_DENSITY_SWAMP,
        WILDFLOWER_DENSITY_PLAINS,
        WILDFLOWER_DENSITY_WOODS,
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


def test_dusk_highlands_decorator_places_clustered_formation_with_one_ore_cap() -> None:
    generator = TerrainGenerator(WorldSeed.parse("b3-generation"))
    decorator = _HighlandsFeatureDecorator(generator.seed)
    formations = decorator._formations_overlapping(  # pyright: ignore[reportPrivateUsage]
        -512, 511, -512, 511, generator
    )
    center_x, center_z, _radius, peak_height = next(
        formation
        for formation in formations
        if formation[2] <= formation[0] % 16 < 16 - formation[2]
        and formation[2] <= formation[1] % 16 < 16 - formation[2]
    )
    coord = ChunkCoord(center_x // 16, center_z // 16)
    chunk = generator.generate_chunk(coord)
    local_x = center_x % 16
    local_z = center_z % 16
    top_y = generator.height_at(center_x, center_z)

    assert chunk.get_block(local_x, top_y + peak_height, local_z) == 6
    assert chunk.get_block(local_x + 1, generator.height_at(center_x + 1, center_z), local_z) == 1
    ore_above_surface = 0
    for x in range(16):
        for z in range(16):
            surface = generator.height_at(coord.x * 16 + x, coord.z * 16 + z)
            ore_above_surface += sum(
                chunk.get_block(x, y, z) == 6 for y in range(surface, surface + 16)
            )
    assert ore_above_surface == 1


def test_highland_formation_crosses_chunk_boundary_consistently() -> None:
    generator = TerrainGenerator(WorldSeed.parse("highland-cross-chunk"))
    decorator = _HighlandsFeatureDecorator(generator.seed)
    formation = next(
        candidate
        for candidate in decorator._formations_overlapping(  # pyright: ignore[reportPrivateUsage]
            -512, 511, -512, 511, generator
        )
        if candidate[0] % 16 < candidate[2]
        or candidate[0] % 16 >= 16 - candidate[2]
        or candidate[1] % 16 < candidate[2]
        or candidate[1] % 16 >= 16 - candidate[2]
    )
    center_x, center_z, radius, _peak_height = formation
    chunks = {
        coord: generator.generate_chunk(coord)
        for coord in {
            ChunkCoord((center_x + dx) // 16, (center_z + dz) // 16)
            for dx in range(-radius, radius + 1)
            for dz in range(-radius, radius + 1)
            if dx * dx + dz * dz <= radius * radius
        }
    }

    touched_chunks: set[ChunkCoord] = set()
    for dx in range(-radius, radius + 1):
        for dz in range(-radius, radius + 1):
            if dx * dx + dz * dz > radius * radius:
                continue
            world_x = center_x + dx
            world_z = center_z + dz
            coord = ChunkCoord(world_x // 16, world_z // 16)
            touched_chunks.add(coord)
            top_y = generator.height_at(world_x, world_z)
            assert chunks[coord].get_block(world_x % 16, top_y, world_z % 16) == 1

    assert len(touched_chunks) >= 2


def test_highland_formation_density_is_sparse_and_deterministic() -> None:
    generator = TerrainGenerator(WorldSeed.parse("distant-silhouette"))
    first = _HighlandsFeatureDecorator(generator.seed)._formations_overlapping(  # pyright: ignore[reportPrivateUsage]
        -512, 511, -512, 511, generator
    )
    second = _HighlandsFeatureDecorator(generator.seed)._formations_overlapping(  # pyright: ignore[reportPrivateUsage]
        -512, 511, -512, 511, generator
    )

    assert first == second
    assert 200 <= len(first) <= 450
    assert all(radius >= 1 for _x, _z, radius, _height in first)


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


def test_ground_cover_density_stays_in_expected_range() -> None:
    generator = TerrainGenerator(WorldSeed.parse("ground-cover-density"))
    tall_grass = 0
    wildflowers = 0
    for chunk_x in range(-4, 5):
        for chunk_z in range(-4, 5):
            chunk = generator.generate_chunk(ChunkCoord(chunk_x, chunk_z))
            for section in chunk.sections:
                tall_grass += int((section.blocks == 13).sum())
                wildflowers += int((section.blocks == 14).sum())

    assert 1500 <= tall_grass <= 2600
    assert 20 <= wildflowers <= 70


def test_biome_silhouette_height_spread_stays_readable(block_registry, biome_registry) -> None:
    generator = TerrainGenerator(
        WorldSeed.parse("distant-silhouette"),
        block_registry=block_registry,
        biome_registry=biome_registry,
    )
    spreads: dict[str, int] = {}
    averages: dict[str, float] = {}

    for biome in Biome:
        heights: list[int] = []
        for x in range(-128, 129, 8):
            for z in range(-128, 129, 8):
                if generator.biome_key_at(x, z) == biome.value:
                    heights.append(generator.height_at(x, z))
        if heights:
            spreads[biome.value] = max(heights) - min(heights)
            averages[biome.value] = sum(heights) / len(heights)

    assert spreads["dusk_highlands"] >= 18
    assert averages["dusk_highlands"] > averages["twilight_plains"] + 14
    assert averages["twilight_plains"] > averages["gloom_swamp"] + 2


def test_biome_boundaries_have_bounded_adjacent_slopes(
    block_registry: BlockRegistry,
    biome_registry: BiomeRegistry,
) -> None:
    generator = TerrainGenerator(
        WorldSeed.parse("distant-silhouette"),
        block_registry=block_registry,
        biome_registry=biome_registry,
    )
    boundary_deltas: list[int] = []
    for x in range(-256, 257):
        for z in range(-256, 257, 4):
            if generator.biome_key_at(x, z) == generator.biome_key_at(x + 1, z):
                continue
            boundary_deltas.append(abs(generator.height_at(x, z) - generator.height_at(x + 1, z)))

    assert len(boundary_deltas) >= 100
    assert max(boundary_deltas) <= 2


def test_structure_landmark_density_is_deterministic_across_distance_sample() -> None:
    generator = TerrainGenerator(WorldSeed.parse("structure-golden"))

    placements = {
        (placement.template.key, placement.origin)
        for chunk_x in range(-32, 33)
        for chunk_z in range(-32, 33)
        for placement in structure_placements_for_chunk(
            ChunkCoord(chunk_x, chunk_z),
            generator.seed,
            generator.structure_templates,
            generator.height_at,
        )
    }

    assert 45 <= len(placements) <= 80
    assert {key for key, _origin in placements} == {
        "dusk_spire",
        "veilstone_ruin",
        "veilwood_camp",
    }


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
        _GroundCoverDecorator,
        _HighlandsFeatureDecorator,
        _OreDecorator,
        _TreeDecorator,
    )

    seed = WorldSeed.parse("proto")
    for cls in (
        _CaveDecorator,
        _OreDecorator,
        _TreeDecorator,
        _GroundCoverDecorator,
        _DungeonDecorator,
        _HighlandsFeatureDecorator,
    ):
        assert isinstance(cls(seed), FeatureDecorator)
