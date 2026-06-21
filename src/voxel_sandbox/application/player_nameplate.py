from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlayerNameplateSnapshot:
    player_id: int
    name: str
    world_position: tuple[float, float, float]
    distance: float
    alpha: float
    visible: bool


def build_player_nameplate_snapshot(
    *,
    player_id: int,
    name: str,
    player_position: tuple[float, float, float],
    camera_position: tuple[float, float, float],
    player_height: float = 1.8,
    max_distance: float = 48.0,
    fade_start: float = 32.0,
) -> PlayerNameplateSnapshot:
    display_name = name.strip()[:32] or f"Player {player_id}"
    world_position = (
        player_position[0],
        player_position[1] + player_height + 0.35,
        player_position[2],
    )
    distance = math.dist(camera_position, world_position)
    alpha = _distance_alpha(distance, fade_start=fade_start, max_distance=max_distance)
    return PlayerNameplateSnapshot(
        player_id=player_id,
        name=display_name,
        world_position=world_position,
        distance=distance,
        alpha=alpha,
        visible=alpha > 0.0,
    )


def _distance_alpha(distance: float, *, fade_start: float, max_distance: float) -> float:
    if distance >= max_distance:
        return 0.0
    if distance <= fade_start:
        return 1.0
    fade_span = max(0.001, max_distance - fade_start)
    return max(0.0, min(1.0, 1.0 - (distance - fade_start) / fade_span))
