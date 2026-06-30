from __future__ import annotations

from voxel_sandbox.application.player_movement_events import (
    PlayerMovementEventState,
    build_player_movement_event_state,
    detect_player_movement_events,
)
from voxel_sandbox.engine.events import PlayerLanded, PlayerWaterTransition
from voxel_sandbox.engine.physics import PlayerController


def test_player_movement_event_state_captures_player_flags() -> None:
    player = PlayerController(x=2.0, y=4.0, z=6.0, on_ground=True, in_water=True)
    player.velocity_y = -1.25

    state = build_player_movement_event_state(player)

    assert state == PlayerMovementEventState(
        position=(2.0, 4.0, 6.0),
        on_ground=True,
        in_water=True,
        vertical_velocity=-1.25,
    )


def test_detect_player_landing_after_fall() -> None:
    previous = PlayerMovementEventState(
        position=(0.0, 8.0, 0.0),
        on_ground=False,
        in_water=False,
        vertical_velocity=-7.5,
    )
    current = PlayerMovementEventState(
        position=(0.0, 4.0, 0.0),
        on_ground=True,
        in_water=False,
        vertical_velocity=0.0,
    )

    assert detect_player_movement_events(previous, current) == (
        PlayerLanded(position=current.position, vertical_velocity=-7.5),
    )


def test_detect_player_landing_ignores_soft_ground_contact() -> None:
    previous = PlayerMovementEventState(
        position=(0.0, 4.2, 0.0),
        on_ground=False,
        in_water=False,
        vertical_velocity=-1.0,
    )
    current = PlayerMovementEventState(
        position=(0.0, 4.0, 0.0),
        on_ground=True,
        in_water=False,
        vertical_velocity=0.0,
    )

    assert detect_player_movement_events(previous, current) == ()


def test_detect_player_water_transitions() -> None:
    dry = PlayerMovementEventState(
        position=(1.0, 5.0, 1.0),
        on_ground=False,
        in_water=False,
        vertical_velocity=-2.0,
    )
    wet = PlayerMovementEventState(
        position=(1.0, 4.0, 1.0),
        on_ground=False,
        in_water=True,
        vertical_velocity=-0.2,
    )

    assert detect_player_movement_events(dry, wet) == (
        PlayerWaterTransition(position=wet.position, entered=True),
    )
    assert detect_player_movement_events(wet, dry) == (
        PlayerWaterTransition(position=dry.position, entered=False),
    )
