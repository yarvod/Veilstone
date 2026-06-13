from __future__ import annotations

import numpy as np
import pytest

from voxel_sandbox.engine.chunks import ChunkSection, DirtyFlag
from voxel_sandbox.engine.world import InMemoryWorld


def test_section_uses_compact_arrays() -> None:
    section = ChunkSection()

    assert section.blocks.shape == (16, 16, 16)
    assert section.blocks.dtype == np.uint16
    assert section.block_light.dtype == np.uint8
    assert section.sky_light.dtype == np.uint8
    assert section.metadata.dtype == np.uint8


def test_setting_block_marks_section_dirty_once_per_change() -> None:
    section = ChunkSection()

    assert section.set_block(1, 2, 3, 4)
    assert section.get_block(1, 2, 3) == 4
    assert section.revision == 1
    assert section.dirty == DirtyFlag.MESH | DirtyFlag.LIGHTING | DirtyFlag.SAVE

    assert not section.set_block(1, 2, 3, 4)
    assert section.revision == 1


def test_section_rejects_invalid_local_coordinates() -> None:
    section = ChunkSection()
    with pytest.raises(IndexError):
        section.get_block(16, 0, 0)


def test_world_get_set_crosses_negative_chunk_boundaries() -> None:
    world = InMemoryWorld()

    world.set_block(-1, 17, -17, 3)

    assert world.get_block(-1, 17, -17) == 3
    chunk = world.get_chunk(-1, -2)
    assert chunk is not None
    assert chunk.get_block(15, 17, 15) == 3


def test_unloaded_and_out_of_height_blocks_are_air() -> None:
    world = InMemoryWorld()
    assert world.get_block(100, 10, 100) == 0
    assert world.get_block(0, -1, 0) == 0
    assert world.get_block(0, 128, 0) == 0
