from __future__ import annotations

from voxel_sandbox.application.player_animation import (
    PlayerAnimationInput,
    PlayerAnimationState,
    PlayerInteraction,
    advance_player_animation,
    start_player_interaction,
)
from voxel_sandbox.application.player_viewmodel import build_player_viewmodel_snapshot
from voxel_sandbox.domain.blocks.registry import create_core_block_registry
from voxel_sandbox.domain.items import ItemStack
from voxel_sandbox.domain.items.registry import create_core_item_registry
from voxel_sandbox.render.player_viewmodel import build_player_viewmodel_render_data


def test_viewmodel_render_data_contains_hand_part() -> None:
    snapshot = build_player_viewmodel_snapshot(None)

    data = build_player_viewmodel_render_data(snapshot)

    assert len(data.parts) == 2
    arm, hand = data.parts
    assert arm.name == "right_arm"
    assert arm.position == snapshot.base_position
    assert arm.scale == (0.24, 0.28, 0.24)
    assert hand.name == "right_hand"
    assert hand.position[1] < arm.position[1]
    assert hand.scale == (0.235, 0.16, 0.235)
    assert abs(hand.position[0] - arm.position[0]) < 0.02
    assert abs(hand.position[2] - arm.position[2]) < 0.04
    assert hand.color != arm.color


def test_viewmodel_render_data_adds_held_item_part() -> None:
    snapshot = build_player_viewmodel_snapshot(
        None,
        held_stack=ItemStack(item_id=3, count=4),
    )

    data = build_player_viewmodel_render_data(snapshot)

    assert [part.name for part in data.parts] == ["right_arm", "right_hand", "held_item_block"]
    assert data.parts[2].position != data.parts[0].position
    assert data.parts[2].position != data.parts[1].position
    assert data.parts[2].scale == (0.16, 0.16, 0.16)


def test_viewmodel_render_data_uses_block_texture_for_held_block() -> None:
    snapshot = build_player_viewmodel_snapshot(
        None,
        held_stack=ItemStack(item_id=3, count=4),
    )
    data = build_player_viewmodel_render_data(
        snapshot,
        item_registry=create_core_item_registry(),
        block_registry=create_core_block_registry(),
    )

    assert data.parts[2].texture_name == "grass_top"


def test_viewmodel_render_data_keeps_lantern_as_compact_held_block() -> None:
    snapshot = build_player_viewmodel_snapshot(
        None,
        held_stack=ItemStack(item_id=7, count=1),
    )

    data = build_player_viewmodel_render_data(snapshot)

    assert [part.name for part in data.parts] == [
        "right_arm",
        "right_hand",
        "held_item_block",
    ]
    assert data.parts[2].scale == (0.16, 0.16, 0.16)


def test_viewmodel_render_data_applies_bob_and_swing_to_hand() -> None:
    idle = build_player_viewmodel_render_data(build_player_viewmodel_snapshot(None))
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

    arm, hand = data.parts
    idle_arm, idle_hand = idle.parts
    assert arm.position != idle_arm.position
    assert hand.position != idle_hand.position
    assert arm.rotation_degrees[0] < idle_arm.rotation_degrees[0]
    assert hand.rotation_degrees == arm.rotation_degrees


def test_viewmodel_render_data_left_hand_mirrors_cuboid_body() -> None:
    right = build_player_viewmodel_render_data(build_player_viewmodel_snapshot(None))
    left = build_player_viewmodel_render_data(build_player_viewmodel_snapshot(None, hand="left"))

    right_arm, right_hand = right.parts
    left_arm, left_hand = left.parts

    assert right_arm.position[0] == -left_arm.position[0]
    assert right_hand.position[0] == -left_hand.position[0]
    assert right_arm.rotation_degrees[2] == -left_arm.rotation_degrees[2]
    assert right_hand.rotation_degrees[2] == -left_hand.rotation_degrees[2]
