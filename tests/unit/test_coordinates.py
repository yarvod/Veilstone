from __future__ import annotations

import pytest

from voxel_sandbox.engine.chunks import ChunkCoord, SectionCoord, split_world_axis


@pytest.mark.parametrize(
    ("world", "section", "local"),
    [(0, 0, 0), (15, 0, 15), (16, 1, 0), (-1, -1, 15), (-16, -1, 0), (-17, -2, 15)],
)
def test_split_world_axis(world: int, section: int, local: int) -> None:
    assert split_world_axis(world) == (section, local)


def test_section_coord_exposes_parent_chunk() -> None:
    assert SectionCoord(-2, 4, 7).chunk == ChunkCoord(-2, 7)
