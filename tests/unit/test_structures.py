from __future__ import annotations

from pathlib import Path

from voxel_sandbox.engine.chunks import ChunkCoord
from voxel_sandbox.engine.generation import (
    StructurePlacement,
    TerrainGenerator,
    WorldSeed,
    load_structure_templates,
    roll_structure_loot,
    structure_placements_for_chunk,
)


def template_root() -> Path:
    return Path(__file__).parents[2] / "src/voxel_sandbox/engine/generation/structure_templates"


def test_structure_templates_load_with_blocks_and_loot() -> None:
    templates = load_structure_templates(template_root())

    assert {template.key for template in templates} == {
        "dusk_spire",
        "veilstone_ruin",
        "veilwood_camp",
    }
    assert all(template.blocks for template in templates)
    assert all(template.loot for template in templates)


def test_structure_placement_and_loot_are_deterministic() -> None:
    generator = TerrainGenerator(WorldSeed.parse("structure-golden"))
    first: list[StructurePlacement] = []
    second: list[StructurePlacement] = []
    for x in range(-32, 33):
        for z in range(-32, 33):
            coord = ChunkCoord(x, z)
            first.extend(
                structure_placements_for_chunk(
                    coord,
                    generator.seed,
                    generator.structure_templates,
                    generator.height_at,
                )
            )
            second.extend(
                structure_placements_for_chunk(
                    coord,
                    generator.seed,
                    generator.structure_templates,
                    generator.height_at,
                )
            )

    unique = {(placement.template.key, placement.origin) for placement in first}
    assert unique
    assert {key for key, _origin in unique} == {
        "dusk_spire",
        "veilstone_ruin",
        "veilwood_camp",
    }
    assert unique == {(placement.template.key, placement.origin) for placement in second}
    placement = first[0]
    assert roll_structure_loot(
        placement.template, generator.seed, placement.origin
    ) == roll_structure_loot(placement.template, generator.seed, placement.origin)


def test_generated_structure_blocks_match_across_chunk_generation() -> None:
    generator = TerrainGenerator(WorldSeed.parse("structure-chunk"))
    placement = None
    coord = ChunkCoord(0, 0)
    for x in range(-24, 25):
        for z in range(-24, 25):
            candidate_coord = ChunkCoord(x, z)
            candidates = structure_placements_for_chunk(
                candidate_coord,
                generator.seed,
                generator.structure_templates,
                generator.height_at,
            )
            if candidates:
                coord = candidate_coord
                placement = candidates[0]
                break
        if placement is not None:
            break

    assert placement is not None
    first = generator.generate_chunk(coord)
    second = generator.generate_chunk(coord)
    assert all(
        first.get_block(x, y, z) == second.get_block(x, y, z)
        for x in range(16)
        for y in range(128)
        for z in range(16)
    )
    origin_x, origin_y, origin_z = placement.origin
    checked = 0
    for block in placement.template.blocks:
        world_x = origin_x + block.x
        world_z = origin_z + block.z
        if world_x // 16 != coord.x or world_z // 16 != coord.z:
            continue
        assert first.get_block(world_x % 16, origin_y + block.y, world_z % 16) == block.block_id
        checked += 1
    assert checked > 0
