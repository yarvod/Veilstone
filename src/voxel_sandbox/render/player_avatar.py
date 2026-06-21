from __future__ import annotations

from dataclasses import dataclass

from voxel_sandbox.application.player_render import PlayerRenderSnapshot
from voxel_sandbox.engine.ecs import EntityWorld, RenderModel, Transform


@dataclass(frozen=True, slots=True)
class PlayerAvatarRenderData:
    """Render-adapter data for drawing the local player model."""

    transform: Transform
    model: RenderModel


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
            snapshot.yaw_degrees,
        ),
        model=model,
    )


def build_player_avatar_world(snapshot: PlayerRenderSnapshot) -> EntityWorld:
    """Build a transient EntityWorld containing only the local player avatar."""

    data = build_player_avatar_render_data(snapshot)
    world = EntityWorld()
    entity = world.create()
    world.transforms.set(entity, data.transform)
    world.render_models.set(entity, data.model)
    return world
