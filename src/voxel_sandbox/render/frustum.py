from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


class Frustum:
    __slots__ = ("planes",)

    def __init__(self, matrix: NDArray[np.float32]) -> None:
        m = matrix
        self.planes = [
            (
                float(m[3, 0] + m[0, 0]),
                float(m[3, 1] + m[0, 1]),
                float(m[3, 2] + m[0, 2]),
                float(m[3, 3] + m[0, 3]),
            ),
            (
                float(m[3, 0] - m[0, 0]),
                float(m[3, 1] - m[0, 1]),
                float(m[3, 2] - m[0, 2]),
                float(m[3, 3] - m[0, 3]),
            ),
            (
                float(m[3, 0] + m[1, 0]),
                float(m[3, 1] + m[1, 1]),
                float(m[3, 2] + m[1, 2]),
                float(m[3, 3] + m[1, 3]),
            ),
            (
                float(m[3, 0] - m[1, 0]),
                float(m[3, 1] - m[1, 1]),
                float(m[3, 2] - m[1, 2]),
                float(m[3, 3] - m[1, 3]),
            ),
            (
                float(m[3, 0] + m[2, 0]),
                float(m[3, 1] + m[2, 1]),
                float(m[3, 2] + m[2, 2]),
                float(m[3, 3] + m[2, 3]),
            ),
            (
                float(m[3, 0] - m[2, 0]),
                float(m[3, 1] - m[2, 1]),
                float(m[3, 2] - m[2, 2]),
                float(m[3, 3] - m[2, 3]),
            ),
        ]

    def intersects(
        self, minimum: tuple[float, float, float], maximum: tuple[float, float, float]
    ) -> bool:
        min_x, min_y, min_z = minimum
        max_x, max_y, max_z = maximum
        for A, B, C, D in self.planes:
            x = max_x if A > 0 else min_x
            y = max_y if B > 0 else min_y
            z = max_z if C > 0 else min_z
            if A * x + B * y + C * z + D < 0:
                return False
        return True
