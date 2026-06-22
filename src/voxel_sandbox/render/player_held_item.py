from __future__ import annotations

import math
from dataclasses import dataclass

from voxel_sandbox.domain.blocks import BlockRegistry
from voxel_sandbox.domain.items import ItemRegistry
from voxel_sandbox.engine.ecs import HeldItem

type Vec3 = tuple[float, float, float]
type TextureRect = tuple[float, float, float, float]


@dataclass(frozen=True, slots=True)
class PlayerHeldItemRenderData:
    offset: Vec3
    scale: Vec3
    rotation: Vec3
    color: Vec3
    texture_rect: TextureRect | None = None


def build_player_held_item_render_data(
    held_item: HeldItem,
    *,
    arm_offset: Vec3,
    arm_rotation: Vec3,
    item_registry: ItemRegistry | None = None,
    block_registry: BlockRegistry | None = None,
    atlas_uvs: dict[str, TextureRect] | None = None,
) -> PlayerHeldItemRenderData:
    """Build a small cuboid held near the animated hand in model-local space."""

    side = -1.0 if held_item.hand == "right" else 1.0
    hand_offset = _add(arm_offset, _rotate((side * 0.03, -0.43, -0.20), arm_rotation))
    texture_rect = _held_block_texture_rect(
        held_item,
        item_registry=item_registry,
        block_registry=block_registry,
        atlas_uvs=atlas_uvs,
    )
    return PlayerHeldItemRenderData(
        offset=hand_offset,
        scale=(0.22, 0.22, 0.22),
        rotation=_add(arm_rotation, (-0.30, side * 0.45, side * 0.18)),
        color=(0.44, 0.70, 0.32) if texture_rect is not None else (0.95, 0.75, 0.25),
        texture_rect=texture_rect,
    )


def _held_block_texture_rect(
    held_item: HeldItem,
    *,
    item_registry: ItemRegistry | None,
    block_registry: BlockRegistry | None,
    atlas_uvs: dict[str, TextureRect] | None,
) -> TextureRect | None:
    if item_registry is None or block_registry is None or atlas_uvs is None:
        return None
    item = item_registry.by_id(held_item.item_id)
    if item.block_id is None:
        return None
    texture_name = block_registry.by_id(item.block_id).texture_top
    atlas_rect = atlas_uvs.get(texture_name)
    if atlas_rect is None:
        return None
    return _atlas_bounds_to_rect(atlas_rect)


def _atlas_bounds_to_rect(bounds: TextureRect) -> TextureRect:
    return bounds[0], bounds[1], bounds[2] - bounds[0], bounds[3] - bounds[1]


def _add(first: Vec3, second: Vec3) -> Vec3:
    return first[0] + second[0], first[1] + second[1], first[2] + second[2]


def _rotate(value: Vec3, rotation: Vec3) -> Vec3:
    x, y, z = value
    cx, sx = math.cos(rotation[0]), math.sin(rotation[0])
    cy, sy = math.cos(rotation[1]), math.sin(rotation[1])
    cz, sz = math.cos(rotation[2]), math.sin(rotation[2])
    y, z = cx * y + sx * z, -sx * y + cx * z
    x, z = cy * x - sy * z, sy * x + cy * z
    x, y = cz * x + sz * y, -sz * x + cz * y
    return x, y, z
