from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from voxel_sandbox.engine.chunks import SECTION_SIZE, ChunkCoord, SectionCoord, split_world_axis


@pytest.mark.parametrize(
    ("world", "section", "local"),
    [(0, 0, 0), (15, 0, 15), (16, 1, 0), (-1, -1, 15), (-16, -1, 0), (-17, -2, 15)],
)
def test_split_world_axis(world: int, section: int, local: int) -> None:
    assert split_world_axis(world) == (section, local)


@given(st.integers(min_value=-(2**63), max_value=2**63 - 1))
def test_split_world_axis_round_trips_arbitrary_coordinates(world: int) -> None:
    section, local = split_world_axis(world)

    assert 0 <= local < SECTION_SIZE
    assert section * SECTION_SIZE + local == world


def test_section_coord_exposes_parent_chunk() -> None:
    assert SectionCoord(-2, 4, 7).chunk == ChunkCoord(-2, 7)
