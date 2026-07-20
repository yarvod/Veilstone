from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

def propagate_light(
    sources: NDArray[np.uint8],
    opaque: NDArray[np.uint8],
) -> NDArray[np.uint8]: ...
