from __future__ import annotations

from voxel_sandbox.application.player_animation import (
    PlayerAnimationInput,
    PlayerAnimationState,
    advance_player_animation,
)
from voxel_sandbox.application.player_render import build_player_render_snapshot
from voxel_sandbox.engine.physics import PlayerController


def test_build_player_render_snapshot_captures_player_view_data() -> None:
    player = PlayerController(x=3.0, y=64.0, z=-2.0)
    player.velocity_y = -1.5
    player.in_water = True
    player.on_ground = False

    snapshot = build_player_render_snapshot(player, yaw_degrees=725.0)

    assert snapshot.position == (3.0, 64.0, -2.0)
    assert snapshot.eye_position == player.eye_position
    assert snapshot.yaw_degrees == 5.0
    assert snapshot.width == player.width
    assert snapshot.height == player.height
    assert snapshot.in_water is True
    assert snapshot.on_ground is False
    assert snapshot.vertical_velocity == -1.5
    assert snapshot.animation is None


def test_build_player_render_snapshot_is_detached_from_player_mutation() -> None:
    player = PlayerController(x=1.0, y=2.0, z=3.0)
    snapshot = build_player_render_snapshot(player, yaw_degrees=-90.0)

    player.x = 10.0
    player.y = 20.0
    player.z = 30.0

    assert snapshot.position == (1.0, 2.0, 3.0)
    assert snapshot.yaw_degrees == 270.0


def test_build_player_render_snapshot_can_carry_animation_snapshot() -> None:
    player = PlayerController(x=1.0, y=2.0, z=3.0)
    _, animation = advance_player_animation(
        PlayerAnimationState(),
        PlayerAnimationInput(forward=1.0, on_ground=True),
        0.42,
    )

    snapshot = build_player_render_snapshot(
        player,
        yaw_degrees=45.0,
        animation=animation,
    )

    assert snapshot.animation is animation
    assert snapshot.animation is not None
    assert snapshot.animation.footstep_due is True
