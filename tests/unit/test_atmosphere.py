from __future__ import annotations

import math

from voxel_sandbox.render.atmosphere import (
    celestial_light_direction,
    daylight_factor,
    sky_color,
    sun_direction,
)


def test_daylight_peaks_at_noon_and_has_night_floor() -> None:
    assert abs(daylight_factor(0.25) - 1.0) < 1e-9
    assert abs(daylight_factor(0.75) - 0.37) < 1e-9
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


def test_celestial_light_tracks_sun_and_switches_to_moon_at_night() -> None:
    noon = sun_direction(0.25)
    sunset = sun_direction(0.5)
    night_sun = sun_direction(0.75)
    night_light = celestial_light_direction(0.75)

    assert noon[1] > 0.9
    assert abs(sunset[0] + 0.963) < 0.01
    assert night_sun[1] < -0.9
    assert night_light == (-night_sun[0], -night_sun[1], -night_sun[2])
