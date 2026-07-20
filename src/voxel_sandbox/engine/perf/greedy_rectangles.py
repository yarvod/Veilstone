from __future__ import annotations

from collections.abc import Callable

import numpy as np
from numpy.typing import NDArray

GreedyRectangle = tuple[int, int, int, int, int]
GreedyRectangleScanner = Callable[
    [NDArray[np.int32], NDArray[np.int32]],
    list[GreedyRectangle],
]


def python_greedy_rectangles(
    signatures: NDArray[np.int32],
    faces: NDArray[np.int32],
) -> list[GreedyRectangle]:
    rectangles: list[GreedyRectangle] = []
    rows, columns = signatures.shape
    for v in range(rows):
        u = 0
        while u < columns:
            signature = int(signatures[v, u])
            if signature < 0:
                u += 1
                continue
            width = 1
            while u + width < columns and int(signatures[v, u + width]) == signature:
                width += 1
            height = 1
            while v + height < rows and np.all(signatures[v + height, u : u + width] == signature):
                height += 1
            face_index = int(faces[v, u])
            signatures[v : v + height, u : u + width] = -1
            rectangles.append((u, v, width, height, face_index))
            u += width
    return rectangles


try:
    from voxel_sandbox.engine.perf.cy_greedy import greedy_rectangles as _native_scanner
except ImportError:
    _native_scanner: GreedyRectangleScanner | None = None


NATIVE_GREEDY_RECTANGLES = _native_scanner is not None
greedy_rectangles: GreedyRectangleScanner = _native_scanner or python_greedy_rectangles
