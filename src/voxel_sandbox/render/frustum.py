from __future__ import annotations

import itertools

import numpy as np
from numpy.typing import NDArray


def aabb_intersects_frustum(
    matrix: NDArray[np.float32],
    minimum: tuple[float, float, float],
    maximum: tuple[float, float, float],
) -> bool:
    corners = np.asarray(
        [(*position, 1.0) for position in itertools.product(*zip(minimum, maximum, strict=True))],
        dtype=np.float32,
    )
    clip = (matrix @ corners.T).T
    x, y, z, w = clip[:, 0], clip[:, 1], clip[:, 2], clip[:, 3]
    return not (
        np.all(x < -w)
        or np.all(x > w)
        or np.all(y < -w)
        or np.all(y > w)
        or np.all(z < -w)
        or np.all(z > w)
    )
