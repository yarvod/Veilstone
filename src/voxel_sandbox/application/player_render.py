from __future__ import annotations

from dataclasses import dataclass

from voxel_sandbox.application.player_animation import PlayerAnimationSnapshot
from voxel_sandbox.domain.items import ItemStack
from voxel_sandbox.engine.physics import PlayerController


@dataclass(frozen=True, slots=True)
class PlayerHeldItemSnapshot:
    item_id: int
    count: int
    hand: str = "right"


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
    head_pitch_degrees: float = 0.0
    name: str = "Player"
    health: float = 20.0
    max_health: float = 20.0
    status_flags: tuple[str, ...] = ()
    animation: PlayerAnimationSnapshot | None = None
    held_item: PlayerHeldItemSnapshot | None = None


def build_player_render_snapshot(
    player: PlayerController,
    *,
    yaw_degrees: float,
    head_pitch_degrees: float = 0.0,
    name: str = "Player",
    health: float = 20.0,
    max_health: float = 20.0,
    animation: PlayerAnimationSnapshot | None = None,
    held_stack: ItemStack | None = None,
    hand: str = "right",
) -> PlayerRenderSnapshot:
    """Create render view data without importing Pyglet/ModernGL."""

    return PlayerRenderSnapshot(
        position=(player.x, player.y, player.z),
        eye_position=player.eye_position,
        yaw_degrees=yaw_degrees % 360.0,
        head_pitch_degrees=max(-89.0, min(89.0, head_pitch_degrees)),
        width=player.width,
        height=player.height,
        in_water=player.in_water,
        on_ground=player.on_ground,
        vertical_velocity=player.velocity_y,
        name=name[:32] or "Player",
        health=max(0.0, min(health, max_health)),
        max_health=max_health,
        status_flags=_status_flags(player),
        animation=animation,
        held_item=_held_item_snapshot(held_stack, hand=hand),
    )


def _held_item_snapshot(stack: ItemStack | None, *, hand: str) -> PlayerHeldItemSnapshot | None:
    if stack is None:
        return None
    return PlayerHeldItemSnapshot(item_id=stack.item_id, count=stack.count, hand=hand)


def _status_flags(player: PlayerController) -> tuple[str, ...]:
    flags: list[str] = []
    if player.in_water:
        flags.append("swimming")
    if not player.on_ground:
        flags.append("airborne")
    return tuple(flags)
