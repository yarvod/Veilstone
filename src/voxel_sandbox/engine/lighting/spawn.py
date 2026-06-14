from __future__ import annotations


def effective_light_level(sky_light: int, block_light: int, daylight: float) -> int:
    """Match gameplay light checks to the day-adjusted light used by the renderer."""
    bounded_daylight = min(max(daylight, 0.0), 1.0)
    adjusted_sky = round(min(max(sky_light, 0), 15) * bounded_daylight)
    return max(adjusted_sky, min(max(block_light, 0), 15))
