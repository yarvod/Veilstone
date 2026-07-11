from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from voxel_sandbox.engine.events import PlayerSwimStroke

_WALK_STEP_SECONDS = 0.42
_SPRINT_STEP_SECONDS = 0.28
_SWIM_STEP_SECONDS = 0.55
_WALK_BOB_AMPLITUDE = 0.04
_SPRINT_BOB_AMPLITUDE = 0.055
_SWIM_BOB_AMPLITUDE = 0.025


class PlayerInteraction(StrEnum):
    IDLE = "idle"
    ATTACK = "attack"
    BREAK_BLOCK = "break_block"
    PLACE_BLOCK = "place_block"


_INTERACTION_DURATIONS = {
    PlayerInteraction.IDLE: 0.0,
    PlayerInteraction.ATTACK: 0.24,
    PlayerInteraction.BREAK_BLOCK: 0.30,
    PlayerInteraction.PLACE_BLOCK: 0.22,
}


@dataclass(frozen=True, slots=True)
class PlayerAnimationInput:
    forward: float = 0.0
    right: float = 0.0
    sprint: bool = False
    on_ground: bool = False
    in_water: bool = False
    vertical_velocity: float = 0.0


@dataclass(frozen=True, slots=True)
class PlayerAnimationState:
    gait_cycle: float = 0.0
    step_index: int = 0
    interaction: PlayerInteraction = PlayerInteraction.IDLE
    interaction_elapsed: float = 0.0


@dataclass(frozen=True, slots=True)
class PlayerAnimationSnapshot:
    moving: bool
    sprinting: bool
    swimming: bool
    grounded: bool
    movement_amount: float
    gait_phase: float
    step_index: int
    footstep_due: bool
    swim_stroke_due: bool
    camera_bob_y: float
    viewmodel_bob_y: float
    interaction: PlayerInteraction
    interaction_progress: float
    interaction_active: bool


def start_player_interaction(
    state: PlayerAnimationState, interaction: PlayerInteraction
) -> PlayerAnimationState:
    if interaction is PlayerInteraction.IDLE:
        return PlayerAnimationState(
            gait_cycle=state.gait_cycle,
            step_index=state.step_index,
        )
    return PlayerAnimationState(
        gait_cycle=state.gait_cycle,
        step_index=state.step_index,
        interaction=interaction,
        interaction_elapsed=0.0,
    )


def advance_player_animation(
    state: PlayerAnimationState,
    animation_input: PlayerAnimationInput,
    delta_time: float,
) -> tuple[PlayerAnimationState, PlayerAnimationSnapshot]:
    dt = max(0.0, delta_time)
    movement_amount = min(
        1.0,
        math.hypot(animation_input.forward, animation_input.right),
    )
    swimming = animation_input.in_water
    grounded = animation_input.on_ground
    moving = movement_amount > 0.01 and (grounded or swimming)
    sprinting = bool(animation_input.sprint and moving and not swimming)

    cadence_seconds = _cadence_seconds(sprinting=sprinting, swimming=swimming)
    cycle_delta = movement_amount * dt / (cadence_seconds * 2.0) if moving else 0.0
    gait_cycle = state.gait_cycle + cycle_delta

    next_step_index = math.floor(gait_cycle * 2.0)
    footstep_due = grounded and moving and next_step_index > state.step_index
    swim_stroke_due = swimming and moving and next_step_index > state.step_index

    interaction, interaction_elapsed = _advance_interaction(state, dt)
    interaction_progress = _interaction_progress(interaction, interaction_elapsed)
    interaction_active = interaction is not PlayerInteraction.IDLE

    next_state = PlayerAnimationState(
        gait_cycle=gait_cycle,
        step_index=next_step_index,
        interaction=interaction,
        interaction_elapsed=interaction_elapsed,
    )
    gait_phase = gait_cycle % 1.0
    camera_bob_y = _bob_offset(
        gait_phase,
        moving=moving,
        sprinting=sprinting,
        swimming=swimming,
    )
    snapshot = PlayerAnimationSnapshot(
        moving=moving,
        sprinting=sprinting,
        swimming=swimming,
        grounded=grounded,
        movement_amount=movement_amount,
        gait_phase=gait_phase,
        step_index=next_step_index,
        footstep_due=footstep_due,
        swim_stroke_due=swim_stroke_due,
        camera_bob_y=camera_bob_y,
        viewmodel_bob_y=camera_bob_y * 1.35,
        interaction=interaction,
        interaction_progress=interaction_progress,
        interaction_active=interaction_active,
    )
    return next_state, snapshot


def build_player_animation_events(
    snapshot: PlayerAnimationSnapshot,
    *,
    position: tuple[float, float, float],
) -> tuple[PlayerSwimStroke, ...]:
    if snapshot.swim_stroke_due:
        return (PlayerSwimStroke(position=position),)
    return ()


def build_player_animation_input(
    *,
    forward: float,
    right: float,
    sprint: bool,
    on_ground: bool,
    in_water: bool,
    vertical_velocity: float,
) -> PlayerAnimationInput:
    return PlayerAnimationInput(
        forward=forward,
        right=right,
        sprint=sprint,
        on_ground=on_ground,
        in_water=in_water,
        vertical_velocity=vertical_velocity,
    )


def _cadence_seconds(*, sprinting: bool, swimming: bool) -> float:
    if swimming:
        return _SWIM_STEP_SECONDS
    if sprinting:
        return _SPRINT_STEP_SECONDS
    return _WALK_STEP_SECONDS


def _bob_offset(
    gait_phase: float,
    *,
    moving: bool,
    sprinting: bool,
    swimming: bool,
) -> float:
    if not moving:
        return 0.0
    if swimming:
        amplitude = _SWIM_BOB_AMPLITUDE
    elif sprinting:
        amplitude = _SPRINT_BOB_AMPLITUDE
    else:
        amplitude = _WALK_BOB_AMPLITUDE
    return math.sin(gait_phase * math.tau) * amplitude


def _advance_interaction(
    state: PlayerAnimationState, delta_time: float
) -> tuple[PlayerInteraction, float]:
    if state.interaction is PlayerInteraction.IDLE:
        return PlayerInteraction.IDLE, 0.0
    elapsed = state.interaction_elapsed + delta_time
    duration = _INTERACTION_DURATIONS[state.interaction]
    if elapsed >= duration:
        return PlayerInteraction.IDLE, 0.0
    return state.interaction, elapsed


def _interaction_progress(interaction: PlayerInteraction, elapsed: float) -> float:
    duration = _INTERACTION_DURATIONS[interaction]
    if duration <= 0.0:
        return 0.0
    return min(1.0, elapsed / duration)
