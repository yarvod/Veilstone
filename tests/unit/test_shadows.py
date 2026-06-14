from __future__ import annotations

import numpy as np

from voxel_sandbox.render.shadows import shadow_map_size, sun_light_matrix


def test_shadow_quality_selects_expected_map_size() -> None:
    assert shadow_map_size("off") == 0
    assert shadow_map_size("low") == 1024
    assert shadow_map_size("medium") == 2048
    assert shadow_map_size("unknown") == 2048


def test_sun_matrix_is_finite_and_stable_inside_one_texel() -> None:
    first = sun_light_matrix((8.0, 32.0, 8.0), map_size=1024)
    second = sun_light_matrix((8.01, 32.0, 8.01), map_size=1024)

    assert first.shape == (4, 4)
    assert np.isfinite(first).all()
    assert np.array_equal(first, second)
