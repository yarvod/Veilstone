from __future__ import annotations

from voxel_sandbox.engine.physics import PlayerController, PlayerInput


def flat_world(x: int, y: int, z: int) -> int:
    del x, z
    return 1 if y <= 0 else 0


def test_player_falls_onto_floor() -> None:
    player = PlayerController(x=0.5, y=3.0, z=0.5)

    for _ in range(120):
        player.update(PlayerInput(), 0.0, 1.0 / 60.0, flat_world)

    assert 0.99 < player.y < 1.01
    assert player.on_ground
    assert player.velocity_y == 0.0


def test_player_cannot_walk_through_wall() -> None:
    def world(x: int, y: int, z: int) -> int:
        return 1 if y <= 0 or (x == 2 and 1 <= y <= 2 and z == 0) else 0

    player = PlayerController(x=0.5, y=1.0, z=0.5, on_ground=True)
    for _ in range(60):
        player.update(PlayerInput(forward=1.0), 0.0, 1.0 / 60.0, world)

    assert player.x < 1.71


def test_player_jumps_only_from_ground() -> None:
    player = PlayerController(x=0.5, y=1.0, z=0.5, on_ground=True)
    player.update(PlayerInput(jump=True), 0.0, 1.0 / 60.0, flat_world)
    first_velocity = player.velocity_y
    player.update(PlayerInput(jump=True), 0.0, 1.0 / 60.0, flat_world)

    assert first_velocity > 0.0
    assert player.velocity_y < first_velocity


def test_player_intersection_prevents_placing_inside_body() -> None:
    player = PlayerController(x=0.5, y=1.0, z=0.5)
    assert player.intersects_block((0, 1, 0))
    assert not player.intersects_block((2, 1, 0))


def test_player_reports_collision_at_current_position() -> None:
    player = PlayerController(x=0.5, y=0.5, z=0.5)
    assert player.collides(flat_world)
