from __future__ import annotations

from dataclasses import dataclass

from voxel_sandbox.engine.events import PlayerLanded, PlayerWaterTransition
from voxel_sandbox.engine.physics import PlayerController

_LANDING_SOUND_VELOCITY = -5.0


@dataclass(frozen=True, slots=True)
class PlayerMovementEventState:
    position: tuple[float, float, float]
    on_ground: bool
    in_water: bool
    vertical_velocity: float


def build_player_movement_event_state(
    player: PlayerController,
) -> PlayerMovementEventState:
    return PlayerMovementEventState(
        position=(player.x, player.y, player.z),
        on_ground=player.on_ground,
        in_water=player.in_water,
        vertical_velocity=player.velocity_y,
    )


def detect_player_movement_events(
    previous: PlayerMovementEventState,
    current: PlayerMovementEventState,
    *,
    landing_sound_velocity: float = _LANDING_SOUND_VELOCITY,
) -> tuple[PlayerLanded | PlayerWaterTransition, ...]:
    events: list[PlayerLanded | PlayerWaterTransition] = []
    if (
        not previous.on_ground
        and current.on_ground
        and previous.vertical_velocity <= landing_sound_velocity
    ):
        events.append(
            PlayerLanded(
                position=current.position,
                vertical_velocity=previous.vertical_velocity,
            )
        )
    if previous.in_water != current.in_water:
        events.append(
            PlayerWaterTransition(
                position=current.position,
                entered=current.in_water,
            )
        )
    return tuple(events)
