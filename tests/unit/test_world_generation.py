from __future__ import annotations

import numpy as np

from voxel_sandbox.engine.chunks import ChunkCoord
from voxel_sandbox.engine.generation import TerrainGenerator, WorldSeed


def test_text_seed_is_stable() -> None:
    assert WorldSeed.parse("veilstone") == WorldSeed.parse("veilstone")
    assert WorldSeed.parse("veilstone") != WorldSeed.parse("other")


def test_height_and_biome_are_deterministic() -> None:
    first = TerrainGenerator(WorldSeed.parse(42))
    second = TerrainGenerator(WorldSeed.parse(42))

    assert first.height_at(-123, 456) == second.height_at(-123, 456)
    assert first.biome_at(-123, 456) == second.biome_at(-123, 456)


def test_generated_chunk_is_deterministic_and_layered() -> None:
    generator = TerrainGenerator(WorldSeed.parse("golden-terrain"))
    first = generator.generate_chunk(ChunkCoord(-2, 3))
    second = generator.generate_chunk(ChunkCoord(-2, 3))

    for first_section, second_section in zip(first.sections, second.sections, strict=True):
        assert np.array_equal(first_section.blocks, second_section.blocks)

    height = generator.height_at(-32, 48)
    assert first.get_block(0, height - 1, 0) == 3
    assert first.get_block(0, height - 2, 0) == 2
    assert first.get_block(0, 0, 0) == 1


def test_generation_adds_caves_ores_and_trees_across_sample() -> None:
    generator = TerrainGenerator(WorldSeed.parse("feature-sample"))
    block_ids: set[int] = set()
    for chunk_x in range(-2, 3):
        for chunk_z in range(-2, 3):
            chunk = generator.generate_chunk(ChunkCoord(chunk_x, chunk_z))
            for section in chunk.sections:
                block_ids.update(int(value) for value in np.unique(section.blocks))

    assert 0 in block_ids
    assert 4 in block_ids
    assert 5 in block_ids
    assert 6 in block_ids
