from __future__ import annotations

from voxel_sandbox.domain.blocks import create_core_block_registry
from voxel_sandbox.engine.chunks import Chunk, ChunkCoord
from voxel_sandbox.engine.lighting import relight_chunk


def test_skylight_blocks_opaque_roof_and_spreads_below_it() -> None:
    chunk = Chunk(ChunkCoord(0, 0))
    for x in range(2, 7):
        for z in range(2, 7):
            chunk.set_block(x, 20, z, 1)

    relight_chunk(chunk, create_core_block_registry())

    assert chunk.sections[2].sky_light[4, 15, 4] == 15
    assert chunk.sections[1].sky_light[4, 4, 4] == 0
    center_below = chunk.sections[1].sky_light[4, 3, 4]
    edge_below = chunk.sections[1].sky_light[2, 3, 4]
    assert 0 < center_below < edge_below < 15
    assert chunk.sections[0].sky_light[10, 10, 10] == 15


def test_lantern_light_propagates_and_is_blocked_by_stone() -> None:
    chunk = Chunk(ChunkCoord(0, 0))
    chunk.set_block(8, 8, 8, 7)
    chunk.set_block(9, 8, 8, 1)

    relight_chunk(chunk, create_core_block_registry())

    section = chunk.sections[0]
    assert section.block_light[8, 8, 8] == 14
    assert section.block_light[7, 8, 8] == 13
    assert section.block_light[9, 8, 8] == 0
    assert section.block_light[8, 8, 10] == 12


def test_removing_lantern_clears_stale_light() -> None:
    chunk = Chunk(ChunkCoord(0, 0))
    chunk.set_block(8, 8, 8, 7)
    registry = create_core_block_registry()
    relight_chunk(chunk, registry)
    chunk.set_block(8, 8, 8, 0)

    relight_chunk(chunk, registry)

    assert chunk.sections[0].block_light.max() == 0
