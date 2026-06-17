from __future__ import annotations

import math


def sun_direction(time_of_day: float) -> tuple[float, float, float]:
    angle = (time_of_day % 1.0) * math.tau
    raw = (math.cos(angle), math.sin(angle), 0.28)
    length = math.sqrt(sum(component * component for component in raw))
    return raw[0] / length, raw[1] / length, raw[2] / length


def celestial_light_direction(time_of_day: float) -> tuple[float, float, float]:
    sun = sun_direction(time_of_day)
    return sun if sun[1] >= 0.0 else (-sun[0], -sun[1], -sun[2])


def daylight_factor(time_of_day: float) -> float:
    """Return ambient daylight for a normalized day position."""
    sun_sin = math.sin((time_of_day % 1.0) * math.tau)
    moon_sin = max(0.0, -sun_sin)
    # The night (moonlight) now provides extra ambient light (up to +0.25)
    return 0.12 + 0.88 * max(0.0, sun_sin) + 0.25 * moon_sin


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
