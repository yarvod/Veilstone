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
        texture_top=_held_block_texture(snapshot, item_registry, block_registry, "top"),
        texture_side=_held_block_texture(snapshot, item_registry, block_registry, "side"),
        texture_bottom=_held_block_texture(snapshot, item_registry, block_registry, "bottom"),
    )
    return (block,)


def _held_block_texture_name(
    snapshot: PlayerViewmodelSnapshot,
    item_registry: ItemRegistry | None,
    block_registry: BlockRegistry | None,
) -> str | None:
    return _held_block_texture(snapshot, item_registry, block_registry, "top")


def _held_block_texture(
    snapshot: PlayerViewmodelSnapshot,
    item_registry: ItemRegistry | None,
    block_registry: BlockRegistry | None,
    face: str,
) -> str | None:
    if item_registry is None or block_registry is None or snapshot.held_item is None:
        return None
    item = item_registry.by_id(snapshot.held_item.item_id)
    if item.block_id is None:
        return None
    block = block_registry.by_id(item.block_id)
    if face == "side":
        return block.texture_side
    if face == "bottom":
        return block.texture_bottom
    return block.texture_top


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
