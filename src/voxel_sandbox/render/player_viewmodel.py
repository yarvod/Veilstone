from __future__ import annotations

from dataclasses import dataclass

from voxel_sandbox.application.player_viewmodel import PlayerViewmodelSnapshot

type Vec3 = tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class ViewmodelPart:
    name: str
    position: Vec3
    scale: Vec3
    rotation_degrees: Vec3
    color: Vec3


@dataclass(frozen=True, slots=True)
class PlayerViewmodelRenderData:
    parts: tuple[ViewmodelPart, ...]


def build_player_viewmodel_render_data(
    snapshot: PlayerViewmodelSnapshot,
) -> PlayerViewmodelRenderData:
    """Convert application viewmodel pose data into renderable cuboid parts."""
    hand_position = _add(snapshot.base_position, snapshot.bob_offset, snapshot.swing_offset)
    arm = ViewmodelPart(
        name=f"{snapshot.hand}_arm",
        position=hand_position,
        scale=(0.18, 0.62, 0.18),
        rotation_degrees=_add(
            (-22.0, 0.0, -24.0 if snapshot.hand == "right" else 24.0),
            snapshot.swing_rotation_degrees,
        ),
        color=(0.78, 0.58, 0.42),
    )
    if snapshot.held_item is None:
        return PlayerViewmodelRenderData(parts=(arm,))
    return PlayerViewmodelRenderData(parts=(arm, *_held_item_parts(snapshot, hand_position)))


def _held_item_parts(
    snapshot: PlayerViewmodelSnapshot,
    hand_position: Vec3,
) -> tuple[ViewmodelPart, ...]:
    assert snapshot.held_item is not None
    if snapshot.held_item.item_id == 7:
        handle_position = _add(hand_position, (-0.10, 0.40, -0.10))
        rotation = _add((-8.0, 0.0, 8.0), snapshot.swing_rotation_degrees)
        handle = ViewmodelPart(
            name="held_item_lantern_handle",
            position=handle_position,
            scale=(0.055, 0.34, 0.055),
            rotation_degrees=rotation,
            color=(0.22, 0.14, 0.08),
        )
        head = ViewmodelPart(
            name="held_item_lantern_head",
            position=_add(handle_position, (0.0, 0.23, 0.0)),
            scale=(0.13, 0.13, 0.13),
            rotation_degrees=rotation,
            color=(1.0, 0.72, 0.08),
        )
        return handle, head
    block = ViewmodelPart(
        name="held_item_block",
        position=_add(hand_position, (-0.11, 0.38, -0.12)),
        scale=(0.20, 0.20, 0.20),
        rotation_degrees=_add((-14.0, 20.0, 8.0), snapshot.swing_rotation_degrees),
        color=(0.64, 0.66, 0.62),
    )
    return (block,)


def _add(*vectors: Vec3) -> Vec3:
    return (
        sum(vector[0] for vector in vectors),
        sum(vector[1] for vector in vectors),
        sum(vector[2] for vector in vectors),
    )
