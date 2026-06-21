from __future__ import annotations

import math

from voxel_sandbox.application.player_animation import (
    PlayerAnimationInput,
    PlayerAnimationState,
    PlayerInteraction,
    advance_player_animation,
    start_player_interaction,
)


def test_walking_advances_gait_and_emits_footstep_contact() -> None:
    state = PlayerAnimationState()

    state, snapshot = advance_player_animation(
        state,
        PlayerAnimationInput(forward=1.0, on_ground=True),
        0.21,
    )

    assert snapshot.moving is True
    assert snapshot.grounded is True
    assert math.isclose(snapshot.gait_phase, 0.5)
    assert snapshot.step_index == 1
    assert snapshot.footstep_due is True
    assert math.isclose(snapshot.camera_bob_y, 0.0, abs_tol=1e-7)
    assert state.step_index == 1


def test_sprinting_uses_faster_cadence_and_larger_bob() -> None:
    walking_state, walking = advance_player_animation(
        PlayerAnimationState(),
        PlayerAnimationInput(forward=1.0, on_ground=True),
        0.07,
    )
    sprint_state, sprinting = advance_player_animation(
        PlayerAnimationState(),
        PlayerAnimationInput(forward=1.0, sprint=True, on_ground=True),
        0.07,
    )

    assert walking_state.gait_cycle < sprint_state.gait_cycle
    assert sprinting.sprinting is True
    assert abs(sprinting.camera_bob_y) > abs(walking.camera_bob_y)


def test_airborne_movement_does_not_emit_footsteps() -> None:
    state, snapshot = advance_player_animation(
        PlayerAnimationState(),
        PlayerAnimationInput(forward=1.0, on_ground=False),
        0.5,
    )

    assert snapshot.moving is False
    assert snapshot.footstep_due is False
    assert snapshot.camera_bob_y == 0.0
    assert state.gait_cycle == 0.0


def test_swimming_advances_motion_without_ground_footstep() -> None:
    state, snapshot = advance_player_animation(
        PlayerAnimationState(),
        PlayerAnimationInput(forward=1.0, in_water=True, on_ground=False),
        0.275,
    )

    assert snapshot.moving is True
    assert snapshot.swimming is True
    assert snapshot.footstep_due is False
    assert math.isclose(snapshot.gait_phase, 0.5)
    assert math.isclose(snapshot.viewmodel_bob_y, snapshot.camera_bob_y * 1.35)
    assert state.step_index == 1


def test_interaction_progresses_and_returns_to_idle() -> None:
    state = start_player_interaction(PlayerAnimationState(), PlayerInteraction.ATTACK)

    state, snapshot = advance_player_animation(state, PlayerAnimationInput(), 0.12)

    assert snapshot.interaction is PlayerInteraction.ATTACK
    assert snapshot.interaction_active is True
    assert math.isclose(snapshot.interaction_progress, 0.5)

    state, snapshot = advance_player_animation(state, PlayerAnimationInput(), 0.12)

    assert state.interaction is PlayerInteraction.IDLE
    assert snapshot.interaction is PlayerInteraction.IDLE
    assert snapshot.interaction_active is False
    assert snapshot.interaction_progress == 0.0
