from __future__ import annotations

import math
from dataclasses import dataclass

from voxel_sandbox.application.player_animation import (
    PlayerAnimationSnapshot,
    PlayerInteraction,
)
from voxel_sandbox.domain.items import ItemStack


@dataclass(frozen=True, slots=True)
class HeldItemSnapshot:
    item_id: int
    count: int


@dataclass(frozen=True, slots=True)
class PlayerViewmodelSnapshot:
    hand: str
    held_item: HeldItemSnapshot | None
    base_position: tuple[float, float, float]
    bob_offset: tuple[float, float, float]
    swing_offset: tuple[float, float, float]
    swing_rotation_degrees: tuple[float, float, float]
    interaction: PlayerInteraction
    interaction_progress: float


def build_player_viewmodel_snapshot(
    animation: PlayerAnimationSnapshot | None,
    *,
    held_stack: ItemStack | None = None,
    hand: str = "right",
) -> PlayerViewmodelSnapshot:
    """Build first-person hand/item pose data without importing render code."""
    interaction = animation.interaction if animation is not None else PlayerInteraction.IDLE
    interaction_progress = animation.interaction_progress if animation is not None else 0.0
    bob_offset = _bob_offset(animation, hand)

    return PlayerViewmodelSnapshot(
        hand=hand,
        held_item=_held_item_snapshot(held_stack),
        base_position=(0.68 if hand == "right" else -0.68, -0.92, -0.58),
        bob_offset=bob_offset,
        swing_offset=_swing_offset(interaction, interaction_progress),
        swing_rotation_degrees=_swing_rotation(interaction, interaction_progress),
        interaction=interaction,
        interaction_progress=interaction_progress,
    )


def _held_item_snapshot(stack: ItemStack | None) -> HeldItemSnapshot | None:
    if stack is None:
        return None
    return HeldItemSnapshot(item_id=stack.item_id, count=stack.count)


def _bob_offset(
    animation: PlayerAnimationSnapshot | None,
    hand: str,
) -> tuple[float, float, float]:
    if animation is None:
        return (0.0, 0.0, 0.0)
    if not animation.moving:
        return (0.0, animation.viewmodel_bob_y, 0.0)

    phase = animation.gait_phase * math.tau
    side = 1.0 if hand == "right" else -1.0
    lateral_amplitude = 0.018
    forward_amplitude = 0.026
    if animation.sprinting:
        lateral_amplitude = 0.026
        forward_amplitude = 0.038
    if animation.swimming:
        lateral_amplitude = 0.012
        forward_amplitude = 0.018

    lateral = math.sin(phase) * lateral_amplitude * side
    forward = (1.0 - math.cos(phase)) * -forward_amplitude
    return (lateral, animation.viewmodel_bob_y, forward)


def _swing_offset(interaction: PlayerInteraction, progress: float) -> tuple[float, float, float]:
    if interaction is PlayerInteraction.IDLE:
        return (0.0, 0.0, 0.0)
    swing = _swing_curve(progress)
    downward = -0.22 * swing
    forward = -0.14 * math.sin(progress * math.pi)
    return (0.0, downward, forward)


def _swing_rotation(interaction: PlayerInteraction, progress: float) -> tuple[float, float, float]:
    if interaction is PlayerInteraction.IDLE:
        return (0.0, 0.0, 0.0)
    swing = _swing_curve(progress)
    match interaction:
        case PlayerInteraction.ATTACK | PlayerInteraction.BREAK_BLOCK:
            return (-72.0 * swing, 12.0 * swing, -8.0 * swing)
        case PlayerInteraction.PLACE_BLOCK:
            return (-28.0 * swing, -8.0 * swing, 6.0 * swing)


def _swing_curve(progress: float) -> float:
    clamped = min(1.0, max(0.0, progress))
    return math.sin(clamped * math.pi)
