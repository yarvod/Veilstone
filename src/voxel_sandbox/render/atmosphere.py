from __future__ import annotations

import math


def daylight_factor(time_of_day: float) -> float:
    """Return ambient daylight for a normalized day position."""
    return 0.12 + 0.88 * max(0.0, math.sin((time_of_day % 1.0) * math.tau))


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
