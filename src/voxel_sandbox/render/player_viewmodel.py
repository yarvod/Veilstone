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
    hand = ViewmodelPart(
        name=f"{snapshot.hand}_hand",
        position=hand_position,
        scale=(0.16, 0.34, 0.16),
        rotation_degrees=snapshot.swing_rotation_degrees,
        color=(0.78, 0.58, 0.42),
    )
    if snapshot.held_item is None:
        return PlayerViewmodelRenderData(parts=(hand,))
    item = ViewmodelPart(
        name="held_item",
        position=_add(hand_position, (0.0, 0.09, -0.18)),
        scale=(0.22, 0.22, 0.22),
        rotation_degrees=(
            snapshot.swing_rotation_degrees[0],
            snapshot.swing_rotation_degrees[1] + 18.0,
            snapshot.swing_rotation_degrees[2],
        ),
        color=(0.72, 0.72, 0.72),
    )
    return PlayerViewmodelRenderData(parts=(hand, item))


def _add(*vectors: Vec3) -> Vec3:
    return (
        sum(vector[0] for vector in vectors),
        sum(vector[1] for vector in vectors),
        sum(vector[2] for vector in vectors),
    )
