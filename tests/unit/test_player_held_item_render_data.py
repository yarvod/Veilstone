from __future__ import annotations

import math

from voxel_sandbox.domain.blocks.registry import create_core_block_registry
from voxel_sandbox.domain.items.registry import create_core_item_registry
from voxel_sandbox.engine.ecs import HeldItem
from voxel_sandbox.render.player_held_item import build_player_held_item_render_data


def test_held_block_render_data_uses_block_texture_rect() -> None:
    data = build_player_held_item_render_data(
        HeldItem(item_id=3, count=1),
        arm_offset=(-0.43, 1.07, 0.0),
        arm_rotation=(0.0, 0.0, 0.0),
        item_registry=create_core_item_registry(),
        block_registry=create_core_block_registry(),
        atlas_uvs={"grass_top": (0.25, 0.50, 0.375, 0.625)},
    )

    assert data.texture_rect == (0.25, 0.50, 0.125, 0.125)
    assert data.scale == (0.22, 0.22, 0.22)
    assert data.color == (0.44, 0.70, 0.32)


def test_non_block_held_item_uses_fallback_colored_cube() -> None:
    data = build_player_held_item_render_data(
        HeldItem(item_id=6, count=1),
        arm_offset=(-0.43, 1.07, 0.0),
        arm_rotation=(0.0, 0.0, 0.0),
        item_registry=create_core_item_registry(),
        block_registry=create_core_block_registry(),
        atlas_uvs={},
    )

    assert data.texture_rect is None
    assert data.color == (0.95, 0.75, 0.25)


def test_held_item_hand_side_mirrors_local_offset_and_tilt() -> None:
    right = build_player_held_item_render_data(
        HeldItem(item_id=3, count=1, hand="right"),
        arm_offset=(-0.43, 1.07, 0.0),
        arm_rotation=(0.0, 0.0, 0.0),
    )
    left = build_player_held_item_render_data(
        HeldItem(item_id=3, count=1, hand="left"),
        arm_offset=(0.43, 1.07, 0.0),
        arm_rotation=(0.0, 0.0, 0.0),
    )

    assert right.offset[0] < 0.0
    assert left.offset[0] > 0.0
    assert right.rotation[1] < 0.0
    assert left.rotation[1] > 0.0


def test_held_item_offset_inherits_arm_rotation() -> None:
    idle = build_player_held_item_render_data(
        HeldItem(item_id=3, count=1),
        arm_offset=(-0.43, 1.07, 0.0),
        arm_rotation=(0.0, 0.0, 0.0),
    )
    walking = build_player_held_item_render_data(
        HeldItem(item_id=3, count=1),
        arm_offset=(-0.43, 1.07, 0.0),
        arm_rotation=(math.radians(25.0), 0.0, 0.0),
    )

    assert walking.offset != idle.offset
    assert walking.rotation[0] > idle.rotation[0]
