from __future__ import annotations

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
    assert snapshot.base_position == (1.18, -0.92, -0.28)
    assert snapshot.interaction is PlayerInteraction.IDLE
    assert snapshot.swing_offset == (0.0, 0.0, 0.0)


def test_viewmodel_bob_uses_player_animation_snapshot() -> None:
    _, animation = advance_player_animation(
        PlayerAnimationState(),
        PlayerAnimationInput(forward=1.0, on_ground=True),
        0.105,
    )

    snapshot = build_player_viewmodel_snapshot(animation)

    assert snapshot.bob_offset == (0.0, animation.viewmodel_bob_y, 0.0)
    assert snapshot.held_item is None


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
    assert snapshot.base_position[0] == -1.18
