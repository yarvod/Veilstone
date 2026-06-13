from __future__ import annotations

import numpy as np

from voxel_sandbox.render.frustum import aabb_intersects_frustum


def test_aabb_inside_identity_clip_space_is_visible() -> None:
    matrix = np.identity(4, dtype=np.float32)
    assert aabb_intersects_frustum(matrix, (-0.5, -0.5, -0.5), (0.5, 0.5, 0.5))


def test_aabb_outside_identity_clip_space_is_culled() -> None:
    matrix = np.identity(4, dtype=np.float32)
    assert not aabb_intersects_frustum(matrix, (2.0, 2.0, 2.0), (3.0, 3.0, 3.0))
