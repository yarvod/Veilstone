from __future__ import annotations

from dataclasses import dataclass

from voxel_sandbox.application.player_viewmodel import PlayerViewmodelSnapshot
from voxel_sandbox.domain.blocks import BlockRegistry
from voxel_sandbox.domain.items import ItemRegistry

type Vec3 = tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class ViewmodelPart:
    name: str
    position: Vec3
    scale: Vec3
    rotation_degrees: Vec3
    color: Vec3
    texture_name: str | None = None


@dataclass(frozen=True, slots=True)
class PlayerViewmodelRenderData:
    parts: tuple[ViewmodelPart, ...]


def build_player_viewmodel_render_data(
    snapshot: PlayerViewmodelSnapshot,
    *,
    item_registry: ItemRegistry | None = None,
    block_registry: BlockRegistry | None = None,
) -> PlayerViewmodelRenderData:
    """Convert application viewmodel pose data into renderable cuboid parts."""
    hand_position = _add(snapshot.base_position, snapshot.bob_offset, snapshot.swing_offset)
    arm, hand = _arm_parts(snapshot, hand_position)
    if snapshot.held_item is None:
        return PlayerViewmodelRenderData(parts=(arm, hand))
    return PlayerViewmodelRenderData(
        parts=(
            arm,
            hand,
            *_held_item_parts(
                snapshot,
                hand.position,
                item_registry=item_registry,
                block_registry=block_registry,
            ),
        )
    )


def _held_item_parts(
    snapshot: PlayerViewmodelSnapshot,
    hand_position: Vec3,
    *,
    item_registry: ItemRegistry | None,
    block_registry: BlockRegistry | None,
) -> tuple[ViewmodelPart, ...]:
    assert snapshot.held_item is not None
    side = 1.0 if snapshot.hand == "right" else -1.0
    block = ViewmodelPart(
        name="held_item_block",
        position=_add(hand_position, (-side * 0.04, 0.12, -0.08)),
        scale=(0.16, 0.16, 0.16),
        rotation_degrees=_add(
            (-22.0, side * -30.0, side * 10.0),
            snapshot.swing_rotation_degrees,
        ),
        color=(0.44, 0.70, 0.32),
        texture_name=_held_block_texture_name(snapshot, item_registry, block_registry),
    )
    return (block,)


def _held_block_texture_name(
    snapshot: PlayerViewmodelSnapshot,
    item_registry: ItemRegistry | None,
    block_registry: BlockRegistry | None,
) -> str | None:
    if item_registry is None or block_registry is None or snapshot.held_item is None:
        return None
    item = item_registry.by_id(snapshot.held_item.item_id)
    if item.block_id is None:
        return None
    return block_registry.by_id(item.block_id).texture_top


def _arm_parts(
    snapshot: PlayerViewmodelSnapshot, hand_position: Vec3
) -> tuple[ViewmodelPart, ViewmodelPart]:
    side = 1.0 if snapshot.hand == "right" else -1.0
    rotation = _add((-28.0, side * -6.0, side * -18.0), snapshot.swing_rotation_degrees)
    sleeve = ViewmodelPart(
        name=f"{snapshot.hand}_arm",
        position=hand_position,
        scale=(0.24, 0.28, 0.24),
        rotation_degrees=rotation,
        color=(0.18, 0.36, 0.68),
    )
    hand = ViewmodelPart(
        name=f"{snapshot.hand}_hand",
        position=_add(hand_position, (-side * 0.006, -0.19, -0.02)),
        scale=(0.235, 0.16, 0.235),
        rotation_degrees=rotation,
        color=(0.82, 0.62, 0.44),
    )
    return sleeve, hand


def _add(*vectors: Vec3) -> Vec3:
    return (
        sum(vector[0] for vector in vectors),
        sum(vector[1] for vector in vectors),
        sum(vector[2] for vector in vectors),
    )
