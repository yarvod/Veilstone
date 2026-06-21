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
from voxel_sandbox.render.player_viewmodel import build_player_viewmodel_render_data


def test_viewmodel_render_data_contains_hand_part() -> None:
    snapshot = build_player_viewmodel_snapshot(None)

    data = build_player_viewmodel_render_data(snapshot)

    assert len(data.parts) == 1
    hand = data.parts[0]
    assert hand.name == "right_hand"
    assert hand.position == snapshot.base_position
    assert hand.scale == (0.16, 0.34, 0.16)


def test_viewmodel_render_data_adds_held_item_part() -> None:
    snapshot = build_player_viewmodel_snapshot(
        None,
        held_stack=ItemStack(item_id=3, count=4),
    )

    data = build_player_viewmodel_render_data(snapshot)

    assert [part.name for part in data.parts] == ["right_hand", "held_item"]
    assert data.parts[1].position[2] < data.parts[0].position[2]
    assert data.parts[1].rotation_degrees[1] == 18.0


def test_viewmodel_render_data_applies_bob_and_swing_to_hand() -> None:
    state = start_player_interaction(
        PlayerAnimationState(),
        PlayerInteraction.ATTACK,
    )
    _, animation = advance_player_animation(
        state,
        PlayerAnimationInput(forward=1.0, on_ground=True),
        0.12,
    )
    snapshot = build_player_viewmodel_snapshot(animation)

    data = build_player_viewmodel_render_data(snapshot)

    hand = data.parts[0]
    assert hand.position != snapshot.base_position
    assert hand.rotation_degrees[0] < 0.0
