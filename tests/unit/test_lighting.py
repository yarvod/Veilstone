from __future__ import annotations

from voxel_sandbox.domain.blocks import create_core_block_registry
from voxel_sandbox.engine.chunks import Chunk, ChunkCoord
from voxel_sandbox.engine.lighting import relight_chunk


def test_direct_skylight_stops_below_opaque_block() -> None:
    chunk = Chunk(ChunkCoord(0, 0))
    chunk.set_block(4, 20, 4, 1)

    relight_chunk(chunk, create_core_block_registry())

    assert chunk.sections[2].sky_light[4, 15, 4] == 15
    assert chunk.sections[1].sky_light[4, 4, 4] == 0
    assert chunk.sections[1].sky_light[4, 3, 4] == 0
    assert chunk.sections[0].sky_light[3, 10, 3] == 15


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
