from __future__ import annotations

import math
from enum import StrEnum


class PerspectiveMode(StrEnum):
    FIRST_PERSON = "first_person"
    THIRD_PERSON_BACK = "third_person_back"
    THIRD_PERSON_FRONT = "third_person_front"


_PERSPECTIVE_ORDER = (
    PerspectiveMode.FIRST_PERSON,
    PerspectiveMode.THIRD_PERSON_BACK,
    PerspectiveMode.THIRD_PERSON_FRONT,
)


def cycle_perspective_mode(mode: PerspectiveMode) -> PerspectiveMode:
    index = _PERSPECTIVE_ORDER.index(mode)
    return _PERSPECTIVE_ORDER[(index + 1) % len(_PERSPECTIVE_ORDER)]


def camera_position_for_perspective(
    eye_position: tuple[float, float, float],
    direction: tuple[float, float, float],
    mode: PerspectiveMode,
    *,
    distance: float = 4.0,
    height_offset: float = 0.55,
) -> tuple[float, float, float]:
    if mode is PerspectiveMode.FIRST_PERSON:
        return eye_position
    horizontal_x, horizontal_z = _horizontal_direction(direction)
    sign = -1.0 if mode is PerspectiveMode.THIRD_PERSON_BACK else 1.0
    return (
        eye_position[0] + horizontal_x * distance * sign,
        eye_position[1] + height_offset,
        eye_position[2] + horizontal_z * distance * sign,
    )


def _horizontal_direction(
    direction: tuple[float, float, float],
) -> tuple[float, float]:
    length = math.hypot(direction[0], direction[2])
    if length <= 0.0001:
        return 0.0, -1.0
    return direction[0] / length, direction[2] / length
