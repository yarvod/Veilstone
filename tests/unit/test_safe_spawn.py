from __future__ import annotations

from voxel_sandbox.engine.generation import find_safe_spawn


def test_safe_spawn_moves_away_from_tree_at_preferred_position() -> None:
    def get_block(x: int, y: int, z: int) -> int:
        if y == 9:
            return 1
        if x == 8 and z == 8 and y in {10, 11}:
            return 4
        return 0

    spawn = find_safe_spawn(
        get_block,
        lambda x, z: 10,
        lambda block_id: block_id != 0,
    )

    assert spawn != (8.5, 10.0, 8.5)
    x, y, z = int(spawn[0]), int(spawn[1]), int(spawn[2])
    assert get_block(x, y - 1, z) != 0
    assert get_block(x, y, z) == 0
    assert get_block(x, y + 1, z) == 0


def test_safe_spawn_expands_beyond_the_old_seven_block_radius() -> None:
    prepared: list[tuple[int, int]] = []

    def get_block(x: int, y: int, z: int) -> int:
        if y == 9:
            return 1
        if max(abs(x - 8), abs(z - 8)) <= 7 and y in {10, 11}:
            return 4
        return 0

    spawn = find_safe_spawn(
        get_block,
        lambda x, z: 10,
        lambda block_id: block_id != 0,
        prepare_column=lambda x, z: prepared.append((x, z)),
    )

    assert max(abs(int(spawn[0]) - 8), abs(int(spawn[2]) - 8)) > 7
    assert prepared
