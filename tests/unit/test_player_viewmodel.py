from __future__ import annotations

import pytest

from voxel_sandbox.application.player_animation import (
    PlayerAnimationInput,
    PlayerAnimationState,
    PlayerInteraction,
    advance_player_animation,
    start_player_interaction,
)
from voxel_sandbox.application.player_viewmodel import build_player_viewmodel_snapshot
from voxel_sandbox.domain.items import ItemStack


def test_viewmodel_snapshot_maps_selected_item_without_render_dependencies() -> None:
    snapshot = build_player_viewmodel_snapshot(
        None,
        held_stack=ItemStack(item_id=7, count=12),
    )

    assert snapshot.hand == "right"
    assert snapshot.held_item is not None
    assert snapshot.held_item.item_id == 7
    assert snapshot.held_item.count == 12
    assert snapshot.base_position == (0.68, -0.92, -0.58)
    assert snapshot.interaction is PlayerInteraction.IDLE
    assert snapshot.swing_offset == (0.0, 0.0, 0.0)


def test_viewmodel_bob_uses_player_animation_snapshot() -> None:
    _, animation = advance_player_animation(
        PlayerAnimationState(),
        PlayerAnimationInput(forward=1.0, on_ground=True),
        0.105,
    )

    snapshot = build_player_viewmodel_snapshot(animation)

    assert snapshot.bob_offset[0] == pytest.approx(0.012727922061357854)
    assert snapshot.bob_offset[1] == animation.viewmodel_bob_y
    assert snapshot.bob_offset[2] == pytest.approx(-0.007615223689149762)
    assert snapshot.held_item is None


def test_viewmodel_bob_mirrors_lateral_sway_for_left_hand() -> None:
    _, animation = advance_player_animation(
        PlayerAnimationState(),
        PlayerAnimationInput(forward=1.0, on_ground=True),
        0.105,
    )
    right = build_player_viewmodel_snapshot(animation, hand="right")
    left = build_player_viewmodel_snapshot(animation, hand="left")

    assert left.bob_offset[0] == pytest.approx(-right.bob_offset[0])
    assert left.bob_offset[1:] == right.bob_offset[1:]


def test_viewmodel_sprint_sway_is_stronger_than_walk() -> None:
    _, walk = advance_player_animation(
        PlayerAnimationState(),
        PlayerAnimationInput(forward=1.0, on_ground=True),
        0.105,
    )
    _, sprint = advance_player_animation(
        PlayerAnimationState(),
        PlayerAnimationInput(forward=1.0, sprint=True, on_ground=True),
        0.07,
    )

    walk_snapshot = build_player_viewmodel_snapshot(walk)
    sprint_snapshot = build_player_viewmodel_snapshot(sprint)

    assert abs(sprint_snapshot.bob_offset[0]) > abs(walk_snapshot.bob_offset[0])
    assert abs(sprint_snapshot.bob_offset[2]) > abs(walk_snapshot.bob_offset[2])


def test_attack_interaction_produces_swing_pose() -> None:
    state = start_player_interaction(
        PlayerAnimationState(),
        PlayerInteraction.ATTACK,
    )
    _, animation = advance_player_animation(state, PlayerAnimationInput(), 0.12)

    snapshot = build_player_viewmodel_snapshot(animation)

    assert snapshot.interaction is PlayerInteraction.ATTACK
    assert snapshot.interaction_progress == animation.interaction_progress
    assert snapshot.swing_offset[1] < 0.0
    assert snapshot.swing_rotation_degrees[0] < 0.0


def test_left_hand_mirrors_base_position() -> None:
    snapshot = build_player_viewmodel_snapshot(None, hand="left")

    assert snapshot.hand == "left"
    assert snapshot.base_position[0] == -0.68
