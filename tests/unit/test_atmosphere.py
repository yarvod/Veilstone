from __future__ import annotations

import math

from voxel_sandbox.render.atmosphere import daylight_factor, sky_color


def test_daylight_peaks_at_noon_and_has_night_floor() -> None:
    assert abs(daylight_factor(0.25) - 1.0) < 1e-9
    assert abs(daylight_factor(0.75) - 0.12) < 1e-9
    assert abs(daylight_factor(1.25) - 1.0) < 1e-9


def test_sky_color_blends_between_night_and_day() -> None:
    assert all(
        math.isclose(actual, expected)
        for actual, expected in zip(sky_color(0.0), (0.018, 0.025, 0.065, 1.0), strict=True)
    )
    assert all(
        math.isclose(actual, expected)
        for actual, expected in zip(sky_color(1.0), (0.26, 0.43, 0.62, 1.0), strict=True)
    )
