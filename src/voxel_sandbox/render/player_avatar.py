from __future__ import annotations

import math
from dataclasses import dataclass

from voxel_sandbox.application.player_render import PlayerRenderSnapshot
from voxel_sandbox.engine.ecs import (
    AnimationState,
    EntityWorld,
    HeldItem,
    RenderModel,
    Transform,
)


@dataclass(frozen=True, slots=True)
class PlayerAvatarRenderData:
    """Render-adapter data for drawing the local player model."""

    transform: Transform
    model: RenderModel
    held_item: HeldItem | None = None
    name: str = "Player"
    health: float = 20.0
    max_health: float = 20.0
    head_pitch_degrees: float = 0.0
    status_flags: tuple[str, ...] = ()


def build_player_avatar_render_data(
    snapshot: PlayerRenderSnapshot,
) -> PlayerAvatarRenderData:
    """Convert application player view data into entity renderer inputs."""
    scale = (snapshot.width, snapshot.height, snapshot.width)
    model = RenderModel("remote_player", (0.45, 0.68, 1.0), scale)
    return PlayerAvatarRenderData(
        transform=Transform(
            snapshot.position[0],
            snapshot.position[1],
            snapshot.position[2],
            math.radians(snapshot.yaw_degrees) + math.pi / 2.0,
        ),
        model=model,
        held_item=(
            HeldItem(
                snapshot.held_item.item_id,
                snapshot.held_item.count,
                snapshot.held_item.hand,
            )
            if snapshot.held_item is not None
            else None
        ),
        name=snapshot.name,
        health=snapshot.health,
        max_health=snapshot.max_health,
        head_pitch_degrees=snapshot.head_pitch_degrees,
        status_flags=snapshot.status_flags,
    )


def build_player_avatar_world(snapshot: PlayerRenderSnapshot) -> EntityWorld:
    """Build a transient EntityWorld containing only the local player avatar."""
    data = build_player_avatar_render_data(snapshot)
    world = EntityWorld()
    entity = world.create()
    world.transforms.set(entity, data.transform)
    world.render_models.set(entity, data.model)
    if data.held_item is not None:
        world.held_items.set(entity, data.held_item)
    if snapshot.animation is not None:
        world.animations.set(
            entity,
            AnimationState(
                phase=snapshot.animation.gait_phase,
                speed=snapshot.animation.movement_amount,
            ),
        )
    return world
