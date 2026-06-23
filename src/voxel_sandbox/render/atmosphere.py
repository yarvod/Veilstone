from __future__ import annotations

import math

_DAYLIGHT_KEYFRAMES = (
    (0.0, 0.52),
    (1000 / 24000, 0.88),
    (4320 / 24000, 0.98),
    (0.25, 1.0),
    (11000 / 24000, 0.98),
    (0.5, 0.62),
    (13000 / 24000, 0.37),
    (0.75, 0.37),
    (23000 / 24000, 0.30),
    (1.0, 0.52),
)


def sun_direction(time_of_day: float) -> tuple[float, float, float]:
    angle = (time_of_day % 1.0) * math.tau
    raw = (math.cos(angle), math.sin(angle), 0.28)
    length = math.sqrt(sum(component * component for component in raw))
    return raw[0] / length, raw[1] / length, raw[2] / length


def celestial_light_direction(time_of_day: float) -> tuple[float, float, float]:
    sun = sun_direction(time_of_day)
    return sun if sun[1] >= 0.0 else (-sun[0], -sun[1], -sun[2])


def daylight_factor(time_of_day: float) -> float:
    """Return ambient daylight normalized for the current day position."""
    phase = time_of_day % 1.0
    for index, (start_time, start_light) in enumerate(_DAYLIGHT_KEYFRAMES[:-1]):
        end_time, end_light = _DAYLIGHT_KEYFRAMES[index + 1]
        if start_time <= phase <= end_time:
            span = max(end_time - start_time, 1e-9)
            amount = _smoothstep((phase - start_time) / span)
            return start_light + (end_light - start_light) * amount
    return _DAYLIGHT_KEYFRAMES[-1][1]


def sky_color(daylight: float) -> tuple[float, float, float, float]:
    amount = min(max(daylight, 0.0), 1.0)
    day = (0.26, 0.43, 0.62)
    night = (0.018, 0.025, 0.065)
    return (
        night[0] + (day[0] - night[0]) * amount,
        night[1] + (day[1] - night[1]) * amount,
        night[2] + (day[2] - night[2]) * amount,
        1.0,
    )


def _smoothstep(value: float) -> float:
    amount = min(1.0, max(0.0, value))
    return amount * amount * (3.0 - 2.0 * amount)
