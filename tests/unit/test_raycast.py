from __future__ import annotations

from collections.abc import Callable

from voxel_sandbox.engine.physics import voxel_raycast


def block_getter(blocks: dict[tuple[int, int, int], int]) -> Callable[[int, int, int], int]:
    def get_block(x: int, y: int, z: int) -> int:
        return blocks.get((x, y, z), 0)

    return get_block


def test_dda_hits_block_and_reports_placement_cell() -> None:
    hit = voxel_raycast(
        block_getter({(3, 1, -2): 4}),
        (0.5, 1.5, -1.5),
        (1.0, 0.0, 0.0),
        5.0,
    )

    assert hit is not None
    assert hit.block == (3, 1, -2)
    assert hit.previous == (2, 1, -2)
    assert hit.normal == (-1, 0, 0)
    assert hit.block_id == 4


def test_dda_handles_negative_direction() -> None:
    hit = voxel_raycast(block_getter({(-2, 0, 0): 1}), (0.2, 0.5, 0.5), (-1, 0, 0), 4.0)
    assert hit is not None
    assert hit.block == (-2, 0, 0)
    assert hit.normal == (1, 0, 0)


def test_dda_returns_none_beyond_range() -> None:
    assert voxel_raycast(block_getter({(5, 0, 0): 1}), (0.5, 0.5, 0.5), (1, 0, 0), 3.0) is None
