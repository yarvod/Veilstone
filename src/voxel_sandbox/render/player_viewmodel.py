from __future__ import annotations

from dataclasses import dataclass

from voxel_sandbox.application.player_viewmodel import PlayerViewmodelSnapshot
from voxel_sandbox.domain.blocks import BlockRegistry
from voxel_sandbox.domain.items import ItemRegistry
from voxel_sandbox.render.model_snapshots import (
    BlockModelSnapshot,
    build_item_block_model_snapshot,
)

type Vec3 = tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class ViewmodelPart:
    name: str
    position: Vec3
    scale: Vec3
    rotation_degrees: Vec3
    color: Vec3
    texture_name: str | None = None
    texture_top: str | None = None
    texture_side: str | None = None
    texture_bottom: str | None = None


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
    block_model = _held_item_block_model(snapshot, item_registry, block_registry)
    block = ViewmodelPart(
        name="held_item_block",
        position=_add(hand_position, (-side * 0.04, 0.12, -0.08)),
        scale=(0.16, 0.16, 0.16),
        rotation_degrees=_add(
            (-22.0, side * -30.0, side * 10.0),
            snapshot.swing_rotation_degrees,
        ),
        color=(0.44, 0.70, 0.32),
        texture_name=block_model.texture_top if block_model is not None else None,
        texture_top=block_model.texture_top if block_model is not None else None,
        texture_side=block_model.texture_side if block_model is not None else None,
        texture_bottom=block_model.texture_bottom if block_model is not None else None,
    )
    return (block,)


def _held_item_block_model(
    snapshot: PlayerViewmodelSnapshot,
    item_registry: ItemRegistry | None,
    block_registry: BlockRegistry | None,
) -> BlockModelSnapshot | None:
    if item_registry is None or block_registry is None or snapshot.held_item is None:
        return None
    return build_item_block_model_snapshot(
        snapshot.held_item.item_id,
        item_registry,
        block_registry,
    )


def _arm_parts(
    snapshot: PlayerViewmodelSnapshot, hand_position: Vec3
) -> tuple[ViewmodelPart, ViewmodelPart]:
    side = 1.0 if snapshot.hand == "right" else -1.0
    rotation = _add((-24.0, side * -5.0, side * -14.0), snapshot.swing_rotation_degrees)
    sleeve = ViewmodelPart(
        name=f"{snapshot.hand}_arm",
        position=hand_position,
        scale=(0.275, 0.115, 0.275),
        rotation_degrees=rotation,
        color=(0.13, 0.29, 0.58),
    )
    hand = ViewmodelPart(
        name=f"{snapshot.hand}_hand",
        position=_add(hand_position, (-side * 0.003, -0.12, -0.006)),
        scale=(0.255, 0.145, 0.255),
        rotation_degrees=rotation,
        color=(0.78, 0.56, 0.38),
    )
    return sleeve, hand


def _add(*vectors: Vec3) -> Vec3:
    return (
        sum(vector[0] for vector in vectors),
        sum(vector[1] for vector in vectors),
        sum(vector[2] for vector in vectors),
    )
