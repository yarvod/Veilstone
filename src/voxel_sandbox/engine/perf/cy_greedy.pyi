from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

def greedy_rectangles(
    signatures: NDArray[np.int32],
    faces: NDArray[np.int32],
) -> list[tuple[int, int, int, int, int]]: ...
