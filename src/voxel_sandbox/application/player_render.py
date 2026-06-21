from __future__ import annotations

from dataclasses import dataclass

from voxel_sandbox.engine.physics import PlayerController


@dataclass(frozen=True, slots=True)
class PlayerRenderSnapshot:
    """Presentation-facing player state for a future 3D player renderer."""

    position: tuple[float, float, float]
    eye_position: tuple[float, float, float]
    yaw_degrees: float
    width: float
    height: float
    in_water: bool
    on_ground: bool
    vertical_velocity: float


def build_player_render_snapshot(
    player: PlayerController, *, yaw_degrees: float
) -> PlayerRenderSnapshot:
    """Create render view data without importing Pyglet/ModernGL."""

    return PlayerRenderSnapshot(
        position=(player.x, player.y, player.z),
        eye_position=player.eye_position,
        yaw_degrees=yaw_degrees % 360.0,
        width=player.width,
        height=player.height,
        in_water=player.in_water,
        on_ground=player.on_ground,
        vertical_velocity=player.velocity_y,
    )
