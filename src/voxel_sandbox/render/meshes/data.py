from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True, slots=True)
class MeshData:
    vertices: NDArray[np.float32]
    indices: NDArray[np.uint32]

    @property
    def face_count(self) -> int:
        return int(self.indices.size // 6)

    @property
    def triangle_count(self) -> int:
        return int(self.indices.size // 3)
